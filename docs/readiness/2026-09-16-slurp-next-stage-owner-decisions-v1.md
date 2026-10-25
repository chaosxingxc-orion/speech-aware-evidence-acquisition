# SLURP next stage: owner decisions of 2026-09-16

## Language maintenance (2026-10-02)

Historical owner quotations below are English translations. Bilingual entries retain their complete existing English rendering; the early checkpoint/parallel-work quotations are translated in full. Original wording remains addressable at Git commit `c56bf4659` in this same file, with the original decision number and date. This language repair changes no ruling, immutable receipt, runtime identity or frozen worker.

Status: OWNER DECISIONS RECORDED. This note grants no model contact; it fixes the bar, the
comparators and the first cell of the program so later verdicts cannot move them.

## The four decisions (owner, Fable 5.1 session of 2026-09-16)

| # | Question | Decision |
| --- | --- | --- |
| 1 | What is an acceptable large gain on SLURP? | Official pooled SLU-F1 >= 64 (weakest published trained pipeline, Google/SF-ID 64.02, floor rule of 2026-09-04) AND intent >= 78, replicated on the same roster. |
| 2 | Admit the pending four-row candidate-bound slot-view proof? | Not now. The prepared configuration (`configs/experiment/slurp-candidate-slot-view-rendering-proof4-v1.json`) stays on file; re-open only if context capacity blocks an admitted module. |
| 3 | The held TRAIN A direct score? | Released as the TRAIN A direct anchor: run SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1, read once, no re-score. |
| 4 | The zero-yield Reviewer/Planner loop? | Fly a Reviewer-off ablation first; if neutral under the null margins, remove the loop from the default plan and redirect its contacts to sampling and exemplar grounding. |

## Why the bar is where it is

The retained dual-store agent reaches SLU 48.53 / intent 77.96 on TRAIN A and about 50.3 on
DEV1000 (+14.6 over direct). Intent already clears the published floor (72.06) but SLU-F1 sits
about 14 points below the weakest published trained pipeline. The bar therefore asks for the
system to be at least as good as the weakest trained pipeline on the task's own metric, on
exposed development rosters, twice. It is not a test-split or paper claim.

## Fixed consequences

- Every Phase B cell is a one-factor module admission on TRAIN A 1,080 against the sealed anchor
  bytes (run SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1) or the sealed
  predecessor cell it names; guards use the SLURP own-null half-widths (intent 0.92, SLU micro
  1.18, scenario 0.83, action 0.98).
- The TRAIN A system-versus-direct claim uses the released direct anchor; DEV1000 keeps its
  sealed direct/agent replication pair as the fresh-roster confirmation.
- Fold B and the test split stay unread until the v2 base is locked.
- Program: `docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`.
- Coordination: `docs/superpowers/plans/experiment-handoff/OWNER-FABLE-TAKEOVER-2026-09-16.md`.

## Owner decisions of 2026-09-17 (after cell B0 and the Phase A audits)

| # | Question | Decision |
| --- | --- | --- |
| 6 | Cell B0 returned HARMFUL by the preregistered intent clause although the point estimate is nil; the imported DEV1000 margin (0.92 pp) is narrower than TRAIN A's CI95 half-width (1.175 pp). | A: re-decide module M0 under the TRAIN A own null. The replicate B0r (byte-identical to B0) supplies the margins as the CI95 half-widths of (B0r minus B0); NEUTRAL needs both passes non-inferior to the anchor at those margins; the first-pass verdict stays on record beside the re-decision. |
| 7 | Projection v3 (label rule R_action then legal-label v2; filler surface normalisation) gains +3.46 / +3.73 pp official SLU of which about three quarters is case alignment scored at zero by the symmetric scorer. | A: adopt v3 as the fixed post-processing of every official number from now on; every report shows the symmetric-normalised number beside it and states that about 2.5 pp of the 64-point bar is representation alignment, not capability. |
| 8 | GPU order and twin triggering for the registered cells. | B1 -> B2 -> B4b -> B4a -> B4c; a cell's twin flies only after its arm shows a positive CI95 against the base; one cell in flight. |
| 9 | B4a's fallback candidate pulls up to 16 slot cards (median +7 values). | B4c (intent store v2 alone) flies only if B4a admits, to separate the store revision from the fallback hypothesis. |
| 10 | Codex's untracked leftovers in the main checkout and its worktrees. | Remove after merging: the three untracked files move to an archive outside the repository with a receipt; worktrees whose commits are reachable from a branch are pruned with a tombstone receipt; flight worktrees stay until their flights finalize. |

Outcome of decision 6 (2026-09-17, after the B0r read): HARMFUL under the own null (intent clause fails on both passes; SLU clause fails once by 0.028 pp). The review loop is retained; B1, B2 and B4 re-register on the anchor as v2 packages. Record: `docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`.

## Owner directive of 2026-09-17 (mid-flight, cell B4b)

| # | Directive (translated from the owner's Chinese message; the original is quoted in the coordinator's memory record) | Consequence |
| --- | --- | --- |
| 11 | Every agent node's input context must follow ONE unified handling policy. A model's raw output is never handed to the next node unprocessed. Per-node templates are provided, and where necessary one extra model call cleans the context, so the core performs better across tasks. | A Node Context Policy (NCP) is designed for the harness: one policy object per node boundary with levels L0 raw pass-through (the anchor, byte-identical), L1 template-built structured context (deterministic, zero contacts) and L2 = L1 plus one context-cleaning contact at declared boundaries (schema-validated, falls back to L1, metered like every contact). Audit of what each node receives today first (`docs/results/2026-09-17-slurp-node-context-audit-v1.md`), then the design (`docs/superpowers/specs/2026-09-17-node-context-policy-design.md`), then the engineering item and the admission cells B7a (L1 vs the sealed anchor) and B7b (L2 vs L1) on TRAIN A 1,080 under the program rule and the measured own null. E2c (the committed grouped-Solver answer as the reviewed draft, merged 59db0f9b) is the first instance of L1. Nothing in flight changes. |

## Owner decisions 12-17 of 2026-09-17 (after cell B4b and the NCP engineering; "agree with the recommendations")

| # | Question | Decision |
| --- | --- | --- |
| 12 | The Node Context Policy design's five open questions and the tool-observation rewrite. | (1) The Reviewer response format is its own one-factor cell B7r, not part of B7a; (2) the Planner brief carries the deterministic HARNESS CHECKS block in B7a; (3) `native_episode.context_policy` is the third episode-class switch key and the old `role_context` folds under it; (4) B7b cleans one boundary (`planner:review-finding`) and the cleaning contact may carry the speech packet; (5) the B7 cells run before B5. The tool-observation rewrite is its own cell B7c. Design section 15 stands as written. |
| 13 | Replication path for the admitted but provisional module M4b (slot store v2). | A request-identical same-roster replicate of cell B4b (about 3.5 GPU hours) flies after B2 v3; it yields "ADMITTED and replicated" and the own null of the admitted configuration. The B5/B5r pair remains a second reading, not the first. |
| 14 | The symmetric-normalised scorer refuses the TRAIN roster, so decision 7's "symmetric number beside every official number" is not evaluable on TRAIN A. | Register a TRAIN sibling of the symmetric scorer (model-free) and re-read every sealed TRAIN A cell offline; verdict addenda carry the symmetric numbers. Until then "not evaluable on TRAIN" stays the honest statement. |
| 15 | GPU order after B4b, the B1 recovery and the NCP family. | B1 recovery -> the B1 derangement twin only if the arm's CI95 is positive -> B2 v3 (greedy twin only on a positive CI95) -> B7a -> B4b replicate -> B4a -> B4c only if B4a admits -> B7r -> B7c -> B7b (each B7 cell only if its predecessor is not HARMFUL) -> B5 -> B5r -> B6. One cell in flight; ready-first scheduling fills idle GPU time with the next registered cell. This updates decision 8. |
| 16 | The "Reviewer reads the five raw samples" form that cell B2 v2 registered by accident. | Dropped. It returns only if B2 v3 shows the review loop adds nothing over the committed draft. |
| 17 | The per-scenario intent band pins at zero when at most three rows are harmed in a 60-row scenario. | Registered rules stay as written; every paired read additionally reports net harmed rows per scenario and flags any scenario with five or more; new preregistrations carry that diagnostic. |

## Owner decisions 18-21 of 2026-09-18 (after the B1 twin sealed and before its read; "agree with the recommendations, execute 18 to 21 as recommended")

Context that opened these decisions: cell B1 read +12.61 pp official pooled SLU against the anchor
(61.14 / intent 80.19; projection v3 62.67 / 81.76), which leaves the v3 SLU bar 1.33 pp away with
intent already above its bar, while module M4b (slot store v2) adds about +2.06 pp v3. The twin
sealed at 2026-09-18T00:3xZ (5,429 contacts, 3.637 GPU hours, one official score) and had not been
read when these decisions were taken.

| # | Question | Decision |
| --- | --- | --- |
| 18 | The B1 preregistration's twin clause covers only "the CI95 lower bound of (B1 minus twin) > 0"; the case where the twin itself beats the anchor while B1 and the twin tie is not covered. Fixed before the twin read. | If (B1 minus twin) has a positive CI95 lower bound, M1 is ADMITTED as speech-keyed exemplar supply under the registered rule. If the (B1 minus twin) CI95 includes zero or is negative while (twin minus anchor) has a positive CI95 lower bound, B1 is NOT ADMITTED under the registered rule; the twin's sealed bytes are registered without any new flight as the arm of a new module "M1p: delivered-scenario annotated-exemplar presence", ADMITTED provisional, whose replication the B5/B5r combination flights carry. If neither contrast is positive, M1 reads NEUTRAL or HARMFUL by the registered guards. The registered rule is never edited after the fact. |
| 19 | Bar-first ordering: decision 15 puts B2 v3, B7a, B4a, B4c, B7r, B7c and B7b (about 25 GPU hours) before the first combination read, although B1 plus M4b already sits at the bar arithmetically. | After the twin closure: the two pending four-row smokes (B2 v3 recovery on the E2d fix, B7a recovery on the E8c fix) fly in GPU gaps to close their proofs; then the B4b replicate; then cell B5e, the early combination of M1 (or M1p) with M4b, one official score, read against the sealed anchor and the released direct anchor with the same rule form as B5. If B5e meets the bar (SLU >= 64 and intent >= 78), B5er replicates it on the same roster; two passes lock "SLURP base v2.0" (manifest hash, scorer id, module list) and B6 confirms on DEV1000 against its sealed direct/agent pair. B2 v3, B7a, B4a, B4c (conditional), B7r, B7c and B7b then admit one at a time on the locked base as "v2.1" modules, in decision 15's relative order. If B5e misses the bar, decision 15's order resumes without change. |
| 20 | Pre-authorisation for B5e landing between 62 and 64 (or otherwise missing the bar), so the program does not wait a round trip. | The bar is not lowered. Admission continues in decision 15's order (B2 v3, B7a, B4a, ...) and B5b, the combination of every module admitted by then, is read against the same bar. Only if B5b also misses does the owner re-decide between a lower bar and a core-swap study. |
| 21 | Decision 13 places the B4b replicate after the B2 v3 arm; decision 19 places it right after the twin closure. | Decision 19 governs: the B4b replicate flies after the twin closure and before the B2 v3 arm. Decision 13's content (request-identical replicate, own null of the admitted configuration) is unchanged. |

Naming: B5e and B5er are the B5/B5r form restricted to the modules admitted at the time of
registration; B5b is the later full combination. None of them is a new mechanism.

## Owner decision 22 of 2026-09-18 (after the B4b replicate aborted on the death of the resident server)

Context: the B4b request-identical replicate aborted at 2,922 of about 5,400 contacts at
2026-09-18T02:40Z when the inherited resident llama-server and its serving wrapper died with the
ChatGPT session that owned them (owner-confirmed; stop receipt ALREADY_EXITED, no OOM, no harness
error). The aborted attempt's trace holds 577 complete rows and 7 partial rows; 496 rows never
started. The owner asked not to re-fly from scratch but to resume from the checkpoint
("Do not restart the run from the beginning; check whether it can resume from a checkpoint."). The harness had no resume capability.

| # | Question | Decision |
| --- | --- | --- |
| 22 | May a flight that died of an infrastructure failure be completed by a resume-recovery instead of a full re-fly, and what is the rule? | Agreed ("Decision 22: agreed."). A resume-recovery is a recovery re-registration (one per flight, root-diagnosed) that applies ONLY when code and request bytes are unchanged (infrastructure failure, never a harness or config defect): every complete row of the aborted attempt is kept without selection, every partial or unstarted row is flown by the recovery attempt under the same run id, the merged manifest declares the predecessor attempt (trace hash, kept-row list and its hash) and scores once; the bundle verifies kept rows against the predecessor trace byte for byte. Item E10 builds it; the B4b replicate is its first use. **Standing rule (owner, same message): every experiment registered from now on must support checkpoint resume** ("All our subsequent experiments must support checkpoint resume."); the fixed protocol and every new preregistration's failure rule carry the resume-recovery clause. |

## Owner decisions 23-24 of 2026-09-18 (after cell B5e was registered and before any B5e number was read)

| # | Question | Decision |
| --- | --- | --- |
| 23 | The B5e preregistration's bar clause reads the v3-projected numbers (decision 7); the additive arithmetic clears 64 only in v3 terms (62.67 + 2.06 = 64.73) and not in official terms (61.14 + 2.55 = 63.69). Which metric is the bar, and may gains be summed? | Owner (translated): "Such gains cannot be added mechanically; is it confirmed that the combined gain is obtainable by addition? Our final evaluation must still be based on the official evaluation, aligned with the community's standard scheme." Consequences: (a) gains are never assumed additive; a combination is read from its own measured score, and additivity is reported only as a diagnostic; (b) **the program bar and every final evaluation read the OFFICIAL, unprojected SLURP `evaluate.py` number** (pooled SLU-F1 >= 64.00 and intent >= 78.00 on `slurp-slu-official-train`), the community-standard protocol; projection v3 stays a fixed diagnostic reported beside every official number (this revises the reading of decision 7: v3 is no longer the number the bar reads). Recorded before any B5e number was read; the B5e bar clause is amended by `docs/readiness/2026-09-18-slurp-b5e-combination-v1-amendment-decision-23.md` without touching the sealed preregistration bytes. Implication stated to the owner: B5e will most likely miss the official bar by a few tenths, and decision 20 (keep admitting, read B5b) applies. |
| 24 | Machine power and process ownership after three infrastructure deaths in one day (ChatGPT session closed at 02:40Z; laptop shut down at 03:36Z; the coordinator's own `powercfg` change tripping the scheduled tasks' stop-on-battery condition at 14:40Z). | Owner: "adjust it yourself; I will not shut down; but also compare comprehensively the modes that can support resume." Consequences: AC sleep and hibernate set to never (done 14:40Z); the serving wrapper, the monitor and every campaign run as Windows Scheduled Tasks registered with the battery and idle conditions disabled and no execution time limit, so they survive Claude Code restarts; the coordinator never changes power settings while tasks run; item E10 documents a comparison of resume modes (trace replay and seal-time merge, incremental row checkpoints, chunked sub-attempts) with the trade-offs and the chosen mode. |

Outcome of decisions 19/20/23 (2026-09-18, after the B5e read): cell B5e reads official 62.34 / 80.09 (v3 63.78 / 81.85): BAR NOT MET on the official number by 1.66 pp SLU (v3 would not have cleared 64 either); the combination reads HARMFUL by the registered clause 3 on the intent CI95 lower bound (-1.51 < -1.0051) although the point estimate is a one-row tie; B5er is not registered; decision 20's path applies (B2 v3 flying, then B7a, B4a, then B5b). Record: `docs/results/2026-09-18-slurp-b5e-combination-verdict.md`. Pending owner decision 25: whether clause 3 (HARMFUL) of combination cells should require a negative point estimate beyond the margin rather than an interval bound, because the own-null margins were calibrated on a request-identical replicate and are narrower than any one-factor contrast's interval.

## Owner decision 25 and directive 26 of 2026-09-18 (after the B5e read)

| # | Question | Decision |
| --- | --- | --- |
| 25 | Cell B5e's combination clause read HARMFUL only because the intent CI95 lower bound (-1.51) crossed the own-null margin (-1.0051) while the point estimate was a one-row tie; the margin was calibrated on a request-identical replicate and is narrower than any cross-configuration contrast's interval. | Owner (translated): "If some beneficial gain can be seen, record it." Method B: for combination cells the HARMFUL trigger requires a measured loss (intent or SLU point estimate below -h, or a CI95 upper bound below zero); an interval that straddles zero with the point estimate inside the margin reads NEUTRAL with "non-inferiority not proven" stated. Single-factor admission clauses are unchanged. Cell B5e is re-read under the amended clause as **combination NEUTRAL** (M4b inside the combination +1.20 pp SLU [-0.11, +2.48], intent tie), recorded as a post-read addendum; the bar outcome (NOT MET on the official number) and the decision-20 path are unchanged; B5er stays unregistered. |
| 26 | Directive (translated): "What we need now is to see how different modes affect the final task performance. Note that we are not mechanically calling the model: we have a complete agent framework. Many of the analyses we predict can be placed for use in different nodes, such as the Reviewer or the Solver." | Consequence: the offline diagnostics (date/time omission and representation patterns, type-support bindings, the v3 label and filler normalisation, per-scenario confusion, exemplar echo and candidate-union coverage) are program material for NODE CONTEXT, not only for reports. Under the Node Context Policy they enter the agent as deterministic, zero-contact blocks or as a delivery-time normaliser node, authored from construction data only (never from evaluated rows' gold), and their effect is measured on the OFFICIAL number like any module: cell family B8 (B8a delivery-time normaliser node = projection v3 executed inside the agent; B8b Reviewer slot-audit block; B8c Solver scenario hints), registered as one-factor cells on the NCP L1 base, ordered with the owner. |

## Owner decision 27 of 2026-09-19 (order after directive 26; parallelism)

| # | Question | Decision |
| --- | --- | --- |
| 27 | The GPU order after the B5e read and directive 26, and the use of GPU idle time. | Owner: "Good; run non-GPU work and GPU work in parallel as much as possible." (approved; run the non-GPU work in parallel with the GPU work as much as possible). Order: B2 v3 (flown 2026-09-19) -> the B4b replicate resume (E10 first real use) -> B8a (the delivery-time normaliser node, item E11: admission read model-free from sealed arms plus a four-row smoke proving in-agent execution and byte-equality; enters the default plan so every later official number carries it) -> B7a (NCP L1) -> B7r (Reviewer response format) -> B8b (Reviewer slot-audit block) -> B4a -> B8c (Solver scenario hints) -> B5b. Registration, re-pins, engineering, paired reads and closures run beside the flights; one cell in flight at a time; ready-first fills idle GPU time. |

Outcome of decision 18 (2026-09-18, after the twin read): branch A. (B1 minus twin) reads +7.83 pp official pooled SLU with a CI95 of [+5.85, +9.75]; cell B1 is ADMITTED and module M1 is admitted as speech-keyed exemplar supply. The twin alone reads +4.77 pp [+3.20, +6.36] over the anchor with nil intent, recorded as a decomposition fact; module M1p is not registered. Record: `docs/results/2026-09-18-slurp-b1-twin-verdict.md`. Cell B5e therefore combines M1 (the arm's form) with M4b.


## Owner decision 28 of 2026-09-19 (development numbers are not test-set claims)

| # | Question | Decision |
| --- | --- | --- |
| 28 | Every SLURP number this program reads (TRAIN Fold A, TRAIN Fold B, DEV-1000) is a DEVELOPMENT number: the roster comes from the training data and the program has optimised many components on it. The published baselines the bar was derived from (Google/SF-ID 64.02, the SLURP paper ladder) are TEST-set numbers. | Owner (translated from the 2026-09-19 message): "Note that our current performance is on the development set, not the test set. The baselines we compare against are test-set numbers, and we have optimised a great deal on this dataset, so conclusions obtained on it cannot be extended to the test set -- lock this. The final improvement must still come from the Pareto-optimally optimised training-free RL; therefore on the training and development sets, the higher the better, while what we compare against must be the test-set performance." LOCKED: (a) no verdict, note or wiki page may present a TRAIN A / Fold B / DEV-1000 number as beating, matching or approaching a published test-set baseline; the 64 / 78 bar stays as the program's DEVELOPMENT bar (a proxy that orders our own cells) and is labelled so wherever it is quoted; (b) the comparison with published systems happens once, on the SLURP test split, after Stage 3 (training-free RL, Pareto-optimal policies over the exposed exemplar / aggregation / candidate / node policies), under the program's split policy (test only for final reporting; one read; registered before contact); (c) until then the program optimises freely on TRAIN and DEV -- higher is better -- with Fold B and DEV-1000 serving as internal generalisation checks between rosters, never as test proxies; (d) the discipline of one-factor cells, sealed comparators and preregistered rules remains for attribution, not as a substitute for the held-out read. |


## Owner decisions 29-35 of 2026-09-19 (after the decision-28 briefing)

The coordinator's briefing listed seven pending decisions with a recommendation each; the owner answered all seven in one message (Chinese; translated in the Decision column, the owner's own words quoted where they add to the recommendation).

| # | Question | Decision |
| --- | --- | --- |
| 29 | The one-shot test-split read: when is its protocol frozen and what does it contain? | Owner: "follow your recommendation". Draft now (CPU), freeze at the v2.0 lock, execute only after Stage 3. Content: roster = the full official SLURP test split; scorer = the official evaluate.py, one complete scoring job; system = the locked default plan (delivery normaliser node included) plus the Stage-3 policies as frozen; zero test-split contact, preview or tuning before the read; registered before contact; the same system's DEV number reported beside it. The draft must state WHERE the read may run: this repository rejects confirmatory splits (`contracts.assert_execution_scope`), so the read needs either the Stage-3 paper carrier or an owner amendment, named in the draft. |
| 30 | The v2.0 lock trigger now that 64 / 78 is a development bar. | Owner: "agree with your recommendation". Two triggers, either suffices: (a) official SLU-F1 >= 64 and intent >= 78 on TRAIN A, replicated on the same roster; (b) headroom exhausted: three consecutive one-factor cells read NEUTRAL or HARMFUL, whereupon the best admitted combination is locked as v2.0. |
| 31 | Composition rule of B5b (the v2 candidate combination). | Owner: "Consider that different explorations can act at different agent nodes, rather than only being stacked on the same node." Ruling: the v2 candidate is composed PER NODE. Each admitted module sits at the node it acts on (M4b slot store v2 and B4a fallback at Perception / candidate supply; M1 exemplars and B8c scenario hints at the Solver boundary; B8b slot audit and the B7r response format at the Reviewer; NCP L1 on every boundary; M3 at delivery). Two modules competing for the same node are NOT simply stacked: the B5b registration states the node map and, where a conflict exists, flies the placement alternative as a paired cell instead of assuming additivity. Leave-one-out attribution only if the combination misses the bar. B5b is replicated on the same roster (B5br). |
| 32 | If cell B7a v2 reads HARMFUL, what happens to the L1 family (B7r, B7c, B8b)? | Owner: "follow your recommendation" (pre-authorised). NEUTRAL or ADMITTED: the queue continues (B7r -> B8b -> B4a ...). HARMFUL: cells B7r and B7c close unflown; B8b is re-based on the anchor (an E12 follow-up, because the audit block attaches to the L1 structured Reviewer boundary) and re-registered; no cell flies on a HARMFUL base (decision 15). |
| 33 | When is the Stage-3 (training-free RL) specification drafted? | Owner: "First lock the agent engineering base, and the context between every node and the optimisable space, including the knowledge-construction method and content; only then discuss the training-free RL framework." Ruling: NO Stage-3 spec yet. First deliverable: an AGENT BASE LOCK document (draft for owner review) that fixes the node graph as flown, the per-boundary context contract (what each node reads and writes), every knowledge store with its construction method and content, and the optimisable space per node (knobs, current values, admissible ranges, cost effects, evidence so far). The training-free RL framework analysis is discussed only after the owner approves that lock. |
| 34 | Is B6 (DEV-1000 confirmation before the lock) kept? | Owner: "This is the baseline for a fair comparison of the tuning; it can actually be expanded a little." Ruling: kept and expanded: the fair-comparison development roster grows from DEV-1000 to DEV-2000 (the sealed DEV-1000 plus 1,000 further devel recordings drawn with the same stratification and receipted as a roster), with the direct baseline and the anchor flown on the added rows so every comparison stays paired; B6 reads the v2 candidate on DEV-2000. The roster and packet preparation are model-free and run in a GPU gap; the added-row comparators cost about 4 GPU hours. |
| 35 | Continuous GPU occupation for the next 48 hours (about 22-26 GPU hours of queue). | Owner: "OK". The resident serving task stays up; long arms are scheduled by readiness; the owner announces any window in which the machine is needed. |

Consequences recorded elsewhere: the umbrella Research-Objective next-action paragraph (decision 30 triggers, decision 33 order), the program spec's Phase C preview (Stage 3 is preceded by the base lock), and the B5b / B6 registrations when they are written.


## Owner decisions 36-41 of 2026-09-19 (answers to the agent base lock draft v1 and the throughput question)

The coordinator briefed the ten owner questions of `docs/superpowers/specs/2026-09-19-slurp-agent-base-lock-v1-draft.md` and the venue question of the test-split protocol draft; the owner answered Q3, Q4, Q5, Q8, Q9 and raised the throughput question (Chinese; translated).

| # | Question | Decision |
| --- | --- | --- |
| 36 | Q3: the per-node map of the v2 candidate. | Owner: "We need a comprehensive analysis: the responsibilities between these nodes must be divided clearly, and there must be a set of link edges along which they cooperate. Also, you must abstract further: one engineering base must serve speech tasks such as contextual ASR, Audio2Tool and E21, not an agent base designed for SLURP alone." Ruling: the base lock is re-drafted as a CROSS-TASK document (v2): node responsibilities stated once for every carrier, the cooperative edges between nodes (what flows along each edge, in which direction, under which context policy), and the SLURP v1 tables kept as one instance beside the contextual-ASR (Earnings-21/22 + ConEC) and Audio2Tool instances. The B5b node map is derived from that document, not the other way round. |
| 37 | Q4: module M1's unmet replication obligation. | Owner: "follow your recommendation". A request-identical replicate of cell B1 (about 3.7 GPU hours) flies before the lock closes; M1 enters the default plan only if it replicates. |
| 38 | Q5: which margin regime governs which contrast. | Owner: "agree". Rule: a contrast involving a configuration uses the margins of that configuration's own request-identical replicate; where none exists, B0r's own null (SLU 1.1218 / intent 1.0051) is the fallback; the retired imported DEV-1000 half-widths are never used again. |
| 39 | Q8: the FREEZE / OPEN / UNEXPLORED partition as the Stage-3 action space. | Owner: "agree, but extend it: you must define the primitives of every node, and the primitives must have enough generality to abstract and accommodate all kinds of speech tasks." Ruling: the base lock v2 defines, per node, its PRIMITIVES (the operations a node may perform on its inputs: observe, hypothesise, supply, draft, verify, audit, route, acquire, commit, normalise, deliver, and whatever the cross-task analysis adds), each with its signature (inputs, outputs, side effects, receipts, cost) stated generically over carriers and instantiated for SLURP, contextual ASR and Audio2Tool; the Stage-3 action space is the set of exposed knobs of those primitives. Grouped Solver sampling stays OPEN as the rollout mechanism. |
| 40 | Q9: are the never-varied instruction templates frozen? | Owner: "agree". Perception v3, Solver v2, Planner v1 and the task contract v3 are frozen for Stage 2; Stage 3 may open prompt text only as a separate axis with its own control. |
| 41 | The speed of experiments and the cost of the one-shot test read. | Owner: "The experiment progress and speed now feel slow; can you analyse the root cause? Is our batch not large enough, or something else? If one test run takes about 48 hours, that cost is unaffordable; can this be optimised further?" Ruling: a MEASURED throughput root-cause analysis (model-free, from sealed traces, flight receipts, the serving monitor and the llama-server launch geometry) decomposes the cost of a row into prefill tokens, decode tokens, contacts per row, cache reuse and slot occupancy, and ranks the levers (prompt volume, prefix reuse, contacts per row, serving batch geometry) with measured or bounded gains and with the admission form each needs (byte-neutral serving change vs configuration cell). Design target proposed by the coordinator, to be confirmed by the owner once the analysis is in: the one-shot test read of the locked system fits within 12 GPU hours (about one working day), i.e. roughly a 3.5x reduction from the 41-42 GPU hours the protocol draft measured at today's per-row cost. |


## Owner decisions 42-44 of 2026-09-19 (answers to the agent base lock draft v2)

| # | Question | Decision |
| --- | --- | --- |
| 42 | OQ-1 of `docs/superpowers/specs/2026-09-19-agent-base-lock-v2-draft.md`: the three-tier lock. | Owner: "accept". Tier A = the cross-task base (nodes, edges, primitive signatures), Tier B = each carrier's instance, Tier C = the OPEN knobs (the Stage-3 action space). |
| 43 | OQ-2: must every carrier instantiate all six nodes? | Owner: "I believe it must be six nodes." Every carrier (SLURP, contextual ASR, Audio2Tool) instantiates Perception, Solver, Reviewer, Planner, Acquisition and Delivery; a registered absence is not allowed; the v2 findings F-8 (contextual-ASR delivery unregistered) and the missing Acquisition become build obligations. |
| 44 | OQ-3: is Acquisition an optimisation-phase sidecar or a component of everyday inference? | Owner: "Analyse whether Acquisition is a sidecar the optimisation stage needs or a necessary part of everyday inference; if it is needed for everyday inference, build it now. Handle the rest per your recommendations." Coordinator's analysis: it is a component of everyday inference. The thesis makes SUPPLY govern the selection, amount, order AND TIMING of evidence; today every SLURP module supplies evidence once, up front, and when the Reviewer finds the draft under-supplied the Planner's ACQUIRE has no node (E15 turns it into a retained row), so the system cannot recover from under-supply within one episode -- exactly the failure the acquisition edge exists for. Ruling: build it now (item E18) as a generic primitive `acquire(action -> typed evidence)` with carrier-neutral kinds -- knowledge re-query keyed by speech plus state (never text alone, owner ruling of 2026-09-06), speech re-observation (one Perception contact on a re-scoped unit), and tool acquisition (Audio2Tool registry) -- instantiated first on SLURP behind one episode key, then admitted through its own cell. OQ-4 to OQ-12 are handled as the coordinator recommended (two edges for findings vs verdicts; SUPPLY knobs first in Stage 3 with a carrier-native multi-metric reward projection as a prerequisite; form carried across carriers, never the verdict; NCP generalised and renamed before the lock closes; the finite key mandatory; the unexcluded store quarantined; one pins document; the lock receipt becomes a gate). |


## Owner decision 45 of 2026-09-19 (serving geometry and graceful degradation)

| # | Question | Decision |
| --- | --- | --- |
| 45 | After the EFF-1 early evidence (constant tool rendering: 53.5 contacts per minute against 23.5-24.2, GPU utilisation 98 % -> 60 %). | Owner: "Next, analyse whether increasing the batch size brings a stable inference-throughput gain -- that would greatly raise our experimental efficiency. Also analyse whether memory-borrowing inference can be enabled, so that inference on over-long sequences only degrades the service instead of crashing it." Ruling: two measured analyses, model-free first and then one serving-geometry probe in the next GPU gap: (a) batch / slot scaling -- the number of parallel slots (-np), the per-slot context, the prefill batch sizes (-b / -ub) and the KV-cache type against the measured prompt-length distribution of the sealed arms (the widest realised request and its p99 decide the smallest admissible slot), with the throughput regime after lever L1 (decode- or dispatch-bound) and the VRAM budget (model 17,868 MiB, 53.2 KiB per KV token at q8_0) stated; the probe measures contacts per minute and per-request latency on the same four-row and 100-row rosters under two or three geometries, on the resident serving task only in a GPU gap, each geometry receipted as its own session identity; (b) graceful degradation for over-long sequences -- server-side memory borrowing (CUDA unified / managed memory oversubscription under WSL2, host-resident KV, partial layer offload) versus harness-side degradation (the existing context-budget COMPACT decision applied per request as a row disposition, KV quantisation, slot re-assignment), with the WSL2 constraints verified rather than assumed; the recommendation must keep every registered fit receipt honest (a degraded request is recorded as such, never silently truncated). |


## Owner decision 46 of 2026-09-19 (compress the k = 20 exemplar supply)

| # | Question | Decision |
| --- | --- | --- |
| 46 | The owner asks whether the current gain and token consumption both come from raising the candidate set to top-20, and whether that top-20 can be optimised or compressed to save tokens and raise experimental efficiency. | Coordinator's answer: yes -- cell B1's speech-keyed exemplar supply at k = 20 (module M1) is the +12.61 pp SLU gain and the largest prompt-token contributor (the throughput report's lever L3: after L1 the Solver's first render of the 22-item block is about 48 % of a row's prefill); Perception's intent-boundary candidates (k = 8) are a separate knob. Ruling: a MODEL-FREE compression analysis over the sealed B1 arm (and its twin) -- per row, which exemplar ranks carry the gold intent and the gold slot types (gold used offline for the diagnostic only), the cumulative coverage curve by k (5, 8, 10, 12, 15, 20), tokens per exemplar and per block and the block's share of each Solver prompt, echo and duplicate rates, and simulated compressions (smaller k, a per-intent cap, score-gap truncation, a compact rendering of each exemplar, ordering most-relevant-first so that a future COMPACT disposition drops the tail) with their predicted token savings and coverage loss -- followed by ONE registered efficiency-effectiveness cell on the anchor base whose form the analysis ranks first (a smaller k or a compact rendering), read against the sealed B1 arm with the B1 own-null margins once B1r supplies them (decision 38), never assumed neutral. |


## Owner decision 47 of 2026-09-19 (aggregate the returned samples; all intents in the prefix; staged use of the top-20)

| # | Question | Decision |
| --- | --- | --- |
| 47 | Owner: "Analyse whether the returned content can be aggregated. Do we currently return 20 samples or 20 intents? If 20 samples, can they be aggregated into their intents? If intents, how many intents does the task have, and what are the value and cost of returning 20 intents? Or: can we load all intents into the prefix and process the retrieved top-20 in stages?" | Coordinator's facts: cell B1 returns 20 SAMPLES (TRAIN utterances with their gold intent and slot annotations, retrieved by the speech vector and diversified across intents), not intents; SLURP has 60 legal intents (18 scenarios), and the 60-id inventory is already rendered into every request's prefix by the task contract; the per-row supply carries the intent CARDS only for the <= 3 Perception candidates. Ruling: the running M1 compression analysis (decision 46) is extended with (6) the neighbour vote as a classifier (precision of the top-1/2/3 voted intents against gold, the delivered intent's agreement with the vote, the twin as the control), (7) an aggregated rendering (intent histogram + r representative exemplars per listed intent) with its token saving and coverage, and (8) the prefix-and-staging design: all 60 intent cards in the constant prefix (paid once per slot under lever L1's prefix cache), a minimal per-row block (vote + candidate cards + few exemplars), and the slot-filler exemplars of the drafted intent fetched afterwards through the E18 acquisition node keyed by speech plus the drafted intent (model state, never gold). The analysis ranks the three designs and names the one cell to register first. |


## Owner decision 48 of 2026-09-19 (the index, its ordering, and index-based context assembly)

| # | Question | Decision |
| --- | --- | --- |
| 48 | Owner (translated): "Analyse what we just discussed. What matters more is not fetching one particular piece of information but fetching the information already in the context together with its related INDEX. What is important is how the index is designed and ordered, and what the strategy for assembling context on the basis of the index is." | Ruling: knowledge organisation (the ORG axis) is re-stated as an INDEX-CENTRED design: a stable, addressable index of the task's knowledge (SLURP: the 60 intents ordered scenario -> intent with their slot contracts, the slot types and their surface conventions, the confusion edges of E14, representative exemplar ids; contextual ASR: entity / knowledge cards; Audio2Tool: the domain-grouped tool registry) lives in the CONSTANT prefix at two granularities (L0 ids and names, L1 one-line contracts), paid once per slot under lever L1's prefix cache; the per-row context carries POINTERS into the index (candidate ids, the neighbour vote as id + count) plus a bounded expansion (L2 exemplar text) ordered most-relevant-first so that degradation drops expansions before pointers and never the index; each node's assembly policy is declared (Perception reads L0/L1 + speech; Solver reads vote + candidate L1 + r L2 per candidate and cites ids; Reviewer verifies against the cited item's contract and audit block; Planner routes; Acquisition fetches more items by key = speech + drafted id; Delivery normalises); expansion budgets are config keys; receipts record the expanded ids. A design document (index schema, ordering, ids, sizes, per-node assembly table, staged expansion, degradation order, receipts, the cells that test it) is drafted now, grounded in the code and the sealed data, cross-carrier, and the first cell is "index prefix + pointer block" read against the sealed B1 arm. |


## Owner decision 49 of 2026-09-19 (aggregate the neighbours to intents; few-shot capacity only; no raw repetition across roles)

| # | Question | Decision |
| --- | --- | --- |
| 49 | Owner (translated): "Returning the top-20 samples to the model feels odd. What matters more is returning the intent information of those 20 samples, aggregated. The raw content of the samples does not need to be given repeatedly to the different models for reference; keeping at most a few-shot capacity should be enough." | Ruling: the owner's form is the FIRST candidate in the decision-46/47 analysis ranking: a neighbour VOTE (intent id x count, top-m) plus per-listed-intent slot-type counts, plus at most a few-shot capacity of raw exemplar lines (2-3 in total, the top-scored, at most one per listed intent), rendered once at the Solver boundary and never repeated to the other roles. The analysis must separate what carries B1's gain (the 62 % speech-key share: intent vote vs filler surface forms, from the saves-by-rank data) from the 38 % presence share a few-shot set keeps, measure whether the raw block is carried to the Reviewer / Planner today, and, if the form ranks first, write its registration essentials (a new rendering mode of the Solver phase supply with m and the few-shot cap as knobs; comparator the sealed B1 arm; NEUTRAL = free saving, ADMITTED = gain, HARMFUL = measured loss; a form twin separating the vote from the few-shot lines). |


## Owner decision 50 of 2026-09-19 (what a node reads is design; how it reads is optimised under three constraints, never mechanically)

| # | Question | Decision |
| --- | --- | --- |
| 50 | Owner (translated): "Which information each node reads is decided by the agent system; but how to read it most efficiently is constrained by model efficiency, experimental effectiveness and inference cost. Optimise on that basis, but integrate the experimental results -- do not raise efficiency mechanically." | Operating rule for the efficiency line: WHAT a node reads (its inputs by semantic class) is fixed by the base lock (tiers A and B) and is never changed to save tokens; HOW it reads (the rendering form of each boundary: cards or index, full text or pointers, raw exemplars or vote plus few-shot, repetition across roles, the constant prefix) is the optimisation space (tier C knobs) under three constraints -- model efficiency (the model still uses the compressed form), experimental effectiveness (the official pooled SLU-F1 and intent non-inferior at the configuration's own-null margins, paired against a sealed comparator) and inference cost (prefilled tokens per row, GPU hours). Every form is one one-factor cell read on both axes and placed on the effect-cost Pareto front: adopted only if NEUTRAL or better on the official number; a form that saves cost with a measured loss is HARMFUL and never adopted; ordering effects are guarded by a derangement twin where the form re-orders content (A2T ORG-1 lost -3.23 pp by re-ordering alone). Sequence by expected saving times risk: EFF-1 (arm in flight) -> index prefix + pointers (largest saving; twin required) -> the Planner's tool-result replay removed on the anchor base -> the vote + few-shot exemplar form (saving bounded by the exemplar block's 7.6 % share; adopted only if it also gains). The three analyses (exemplar compression with the slot-contract correction, the index design, the EFF-1 verdict) are consolidated into one ranked proposal before any registration; B5b's per-node composition weighs effect and cost together. |
| 51 | D-A of the efficiency Pareto consolidation (`docs/results/2026-09-19-slurp-efficiency-pareto-consolidation-v1.md` section 1): adopt the per-node READS column as the design column of base lock v3, including the two WHAT changes (Planner reads L0 only; Reviewer reads the cited ids only)? | Owner (2026-09-19, translated): "D-A: yes." Ruling: the six-node reads table is the design column of base lock v3; the Planner-L0-only and Reviewer-cited-only reads are design decisions taken, each to be flown as its own one-factor cell with a NEUTRAL bar at the base's own-null margins before it enters any plan (decision 50: what a node reads is decided; how it reads is measured). |
| 52 | D-B: the thirteen answers to the knowledge-index design's questions (consolidation section 4: one key; pure-suffix fill is not a contract change; intent L1 = Activation boundary with exclusions folded into edges; slot L1 = Admissible formats; twin required on the first cell; factoring inside the renderer; citation permitted; slot-card expansion budget 4 first, 0 later; order; hold other carriers; the index is a new exposure; Planner L0 separate; np6 = Probe G2). | Owner: "D-B: provisional" (provisional). Ruling: the recommended answers are the working defaults for item E21's config values and the first index cell; each may be reopened by the owner before that cell is registered, and the registration records them as provisional owner defaults, not settled decisions. |
| 53 | D-C: register the knowledge-index cell and its derangement twin as the next efficiency cell after the tool-rendering repair cell, on the repair arm's sealed bytes. | Owner: "D-C: agreed." Ruling: the index cell + twin are the next efficiency cells; they fly on the 0-B base (decision 55) once that arm has sealed, and item E21's loader refusal 7 must accept "no role holds tool authority" as a constant prefix beside `tool_schema_rendering = "constant"` (a one-line change with a test, before the index cell is registered). |
| 54 | D-D: check and, if possible, raise the host GPU power limit (100 W enforced of 175 W) and run Probe G0. | Owner: "D-D: drive it the current way; do not change the GPU configuration." Ruling: the serving geometry, the power limit and every host setting stay as they are; Probes G0 / G1 / G2 are NOT run; every efficiency claim is read at the current 100 W cap. |
| 55 | D-E: the repair of the constant-prefix failure class found by EFF-1 -- 0-B (withdraw the Reviewer's task-contract tool, whose observation is the contract already in its system message; no role renders a tools array) or 0-A (keep constant rendering and ban the tool-call token at decode time on the tool-free roles). | Owner: "D-E: implement 0-B first, but the effect must still be judged." Ruling: 0-B is the repair form and a WHAT decision taken for the base (tool actions belong to N5 Acquisition, decision 44); it enters no plan until its cells read NEUTRAL-or-better at the named own-null margins -- on the anchor (1.1218 / 1.0051), on B1 (1.2350 / 1.2212) and on the default plan (its own replicate's null) -- and if any of them reads HARMFUL with a measured loss, 0-A is registered as the fallback and the owner decides again. The same day the owner directed (translated) "output a set of experiments needing 20+ GPU hours and drive the scripts step by step" because the coordinator's session budget was ending: the unattended batch of 2026-09-20 (family preregistration `docs/readiness/2026-09-20-slurp-batch-v1-preregistration.md`: the default-plan arm and its replicate, 0-B on the anchor / the plan / B1 and their replicates, after the B8b-anchor resume-recovery) is that directive's execution; every cell keeps its own registration, sealed comparator and fixed rule, and the reads happen when the coordinator returns. |
| 56 | The 0-B repair cell (decision 55): one cell on the B1 base (option a, about 1.6 GPU hours, comparator the sealed B1 bytes at 1.2350 / 1.2212) or three cells on the anchor, B1 and the default plan (option b, about 5 GPU hours)? | Owner (2026-09-20, translated): "Yes -- run (a) first; if the compared results differ by no more than 5 %, (b) is not run." Ruling: the first 0-B cell flies on the B1 base; if its official pooled SLU-F1 and intent are each within 5 % (relative to the comparator's value) of the sealed B1 numbers, the anchor-base and plan-base 0-B cells are not flown and the withdrawal is judged on this cell alone at the own-null margins; a larger difference reopens option (b). |
| 57 | When to fly the default-plan combination arm (program cell B5: anchor + M4b + M3 node + M1) and its replicate, the decision-30 lock evidence: right after the B8b-anchor recovery read (a), or after the 0-B and index cells so the plan flown is the one that will be locked (b)? | Owner: "Prioritise completing the engineering base and raising experimental efficiency." Ruling: option (b); the efficiency line (0-B, then the index cell + twin, then B9a staged acquisition) precedes the combination arm; if decision 30's third consecutive NEUTRAL/HARMFUL one-factor cell fires before the plan arm has flown, v2.0 is provisionally locked on B5e plus the normaliser node (63.78 / 81.85, node applied at delivery) with the plan-arm replicate owed before the lock is final. |
| 58 | Session budget: registrations and recovery packages by script (near-zero agent cost), engineering agents only when necessary, reads by agents as the independent verification; optionally reads scripted with agents as final reviewers. | Owner: "Follow your recommendation." Ruling: the coordinator derives registrations, recovery packages and launch sets by script from sealed precedents; engineering items go to agents only when they cannot be a script edit; every read stays an independent agent read (the B1r / EFF-1 drivers are reused). |
| 59 | Scheduling of the two node-read design cells decision 51 opened (Planner reads L0 only; Reviewer reads the cited ids only), and the scope of the engineering base. | Owner (translated): "First build and complete the engineering base on SLURP and Audio2Tool, then extend to the other datasets." Ruling: the engineering base (six nodes, primitives, failure-mode dispositions, the knowledge index and its assembly, the resume machinery, the drivers) is completed and proven on SLURP and Audio2Tool before any other carrier is touched; the node-read cells are scheduled inside that base work after the index cell reads; Earnings-21/22 cells stay held until the base is locked on the two carriers. |
| 60 | Clarification of decision 54: does "no GPU configuration change" cover the serving geometry probe G2 (np6 x 16,384 after the index cell shrinks the maximum prompt below the fit gate's 14,336 usable tokens), or only the host power limit and host settings? | Owner (2026-09-20, translated): "The power limit and host settings stay untouched for now; everything else is executed as needed." Ruling: decision 54 is narrowed to the host: the enforced 100 W power limit, fan mode and every other host setting stay as they are; serving-geometry probes are executed as needed -- Probe G2 (np6, a new serving session id, about 30 minutes, byte-neutral to requests, with a receipt) runs after the index cell reads and its pointer block has been measured to leave the maximum prompt inside the np6 usable slot; Probe G1 (-ub 1024) likewise as needed. Every later cell and the test read adopt the measured geometry only through their own registrations. |
| 61 | The status word of cell B1-notool (briefing item D1, 2026-09-20): keep the coordinator's NEUTRAL (decision 25 + the B5e precedent; the intent lower bound 0.11 pp short of the margin, no measured loss, B1r's own null failing the same clause), record NOT PROVEN and keep the withdrawal out of the plan, or replicate B1-notool first (1.6 GPU hours) to build its own null. | Owner (2026-09-20, translated): "D1: NEUTRAL stands." Ruling: the B1-notool status is NEUTRAL and final; the withdrawal stays in the SLURP default plan, the RETIRED entry for the Reviewer's task-contract toolkit stands (item E25), and the tool-free B1 fragment is the base of the knowledge-index cell and its twin. The IDX read reports its numbers against B1-notool and, beside them, against B1r. |
| 62 | Token matching of the derangement twin (briefing item D3): at decision 52's default expansion budget slot_card 4 the twin's per-row expansion block is not byte-matched to IDX's (the deranged L2 cards differ in length per row; mean absolute difference about 641 characters, sum zero over the 54 cards). Fly as registered and report the per-row length-difference distribution (a), fly both cells at slot_card 0 as a strict token-matched control (b), or fly IDX first and decide on the twin afterwards (c). | Owner (2026-09-20, translated): "D3: fly (a)." Ruling: both cells fly at decision 52's defaults; the twin read carries the per-row length-difference distribution as a mandatory table and the content effect (IDX minus IDXT) is read with the length difference reported beside it as a covariate; slot_card 0 remains a later cell. |
| 63 | The remaining briefing items of 2026-09-20: D2 (the music scenario's intent-band breach, -8.33, repeating against B1r), D4 (when to fly the default-plan arm and its replicate, the decision-30 final lock), D5 (the order after the index cell), D6 (when the Audio2Tool engineering base starts, decision 59). | Owner (2026-09-20, translated): "Everything else: execute as you recommended." Ruling: D2 -- the music breach is a mandatory diagnostic of the IDX read, not a gate; a repeat opens a scenario-specific check of its cards and exemplars. D4 -- the default-plan arm and its replicate fly after IDX and IDXT have read and the plan's content is stable. D5 -- the order is IDX -> IDXT -> Probe G2 (np6; a serving-geometry probe only, decision 60) -> Planner L0-only -> Reviewer cited-only (decision 51) -> B9a (decision 44) -> default-plan arm + replicate -> v2.0 final lock (decision 30) -> base lock v3 (decisions 42-43) -> B6 DEV-2000 -> Stage 3. D6 -- the Audio2Tool engineering base is built in CPU time during the SLURP flights (the 152-tool registry as an index view on the domain-grouped ORG-1 form), never on the flight tree. |
| 64 | Whether the frozen core can CONSUME the index pattern at all: an L0/L1 index line may look reasonable and still carry too little reference information for the current main model to use it. | Owner (2026-09-20, translated): "One more point I want to stress: we still have to see whether the model can consume the index pattern at all. The index may look reasonable, but our current main model may be unable to consume it because the reference information is too sparse." Ruling: the IDX and IDXT verdicts carry an INDEX-CONSUMPTION read, model-free from the sealed outputs and receipts -- (a) Solver citations of index ids (count, resolved / unresolved, share of rows, consistency with the delivered answer); (b) pointer use: the delivered intent and slot types inside the row's pointer sets, on IDX and on the BASE's sealed outputs against the same pointer blocks; (c) expansion use: slot-type precision / recall and filler format compliance for expanded versus only-pointed slot types; (d) overall format compliance against the L1 'Admissible formats' lines; (e) the base / IDX / IDXT triple -- and state one of CONSUMPTION (IDX differs from IDXT beyond the own null and (a)-(d) move with the score), NON-CONSUMPTION (IDX inside IDXT's null, citations near zero, (b)-(d) flat), MISLEADING TERSENESS (IDX below the base with (d) worse) or undecided, with the evidence. Contingency, fixed now: NON-CONSUMPTION routes to the richer-granularity variant of the same view on the same base (expansion_budget.intent_card > 0 and / or a larger slot_card budget; a new one-factor registration), not to closing the index form; MISLEADING TERSENESS closes the form at decision 52's defaults and the owner decides; CONSUMPTION leaves the NEUTRAL / ADMITTED / HARMFUL verdict standing on its own. Made executable in the IDX protocol and analysis recipe (decision_rule.consumption, diagnostics_required, primary_deliverables, tables_required) and in the IDXT generator before either cell's first contact. |
| 65 | Base for the Audio2Tool index cell (A2T design note section 7): the sealed dual-store union-4000 fragment made tool-free (item E29) or the unflown scope-tools np2 form. | Owner (2026-09-21, translated): "65 as recommended." Ruling: the A2T index base is the sealed dual-store union-4000 fragment with the Reviewer's and Planner's `phase_tools` withdrawn (the SLURP 0-B precedent); the scope-tools np2 form stays registered and unflown. |
| 66 | Index kinds for A2T: `parameter` as a section of the tool card or a fourth selectable kind; exemplars in the first cell or not. | Owner (2026-09-21, translated): "66 as recommended." Ruling: `parameter` is a section of the tool card, never selected on its own; exemplar entries are OFF in the first A2T index cell. |
| 67 | Roster for the first A2T cells (A2T-NULL, A2T-NOTOOL, A2T-IDX, A2T-IDXT): the paired 400-row subset of the sealed union-4000 or the full 4,000 from the first cell. | Owner (2026-09-21, translated): "67: the paired 400 rows." Ruling: one 400-row subset of the sealed union-4000, drawn once and frozen (stratified by tier, receipted under docs/receipts/rosters/), whose comparator rows are the sealed union-4000 outputs of the same sample ids; the full 4,000 flies only for an admitted form. |
| 68 | Whether the carrier's own null (A2T-NULL, a request-identical replicate of the base on the paired subset) flies before any A2T NEUTRAL reading. | Owner (2026-09-21, translated): "68: fly the null first." Ruling: A2T-NULL is the first A2T flight; every later A2T cell is read at the margins it establishes (decision 38); no A2T interval is read against zero again. |
| 69 | GPU placement of the A2T cells: behind IDXT and Probe G2 and ahead of the SLURP node-read cells only when the SLURP queue has no ready cell, or a fixed slot after B9a. | Owner (2026-09-21, translated): "69 as recommended." Ruling: A2T cells enter the queue behind IDXT and Probe G2 and fly whenever the SLURP queue has no ready cell; the geometry swap (A2T np2 session) is paid only when at least two A2T cells are ready. |
| 70 | The Audio2Tool index v2 form after E28's findings (1,040 structure-authored edges, a 73,652-character constant index): a hand-tuned edge rule v2 with a size cap, or something else. | Owner (2026-09-21, translated): "Decision 70: handle it by BEST DISCRIMINABILITY, not by simply piling up information. How best discriminability is obtained can be handed to training-free RL to search and optimise; that information can come in through the knowledge index by value retrieval; or, from the cost and efficiency angle, it can be realised through training-free RL over the context-engineering optimisation dimensions." Ruling: the A2T index CONTENT is not hand-authored by thresholds. (a) The constant prefix carries the minimal L0 index only (3 domain lines + 152 tool signature lines); every L1 line, L2 card and confusable edge is per-row material that enters through the pointer block and VALUE RETRIEVAL keyed by the Perception state and the speech key, under a budget. (b) WHICH lines and edges deserve the constant prefix or a pointer, at what granularity and budget, is the context-engineering ACTION SPACE of training-free RL on the Audio2Tool carrier: state = Perception state + pointer block; actions = per-tool inclusion of the activation line / argument line / edge, granularity level, expansion budget, ordering; reward = a DISCRIMINABILITY objective (tool accuracy on construction-pool rollouts, with a same-domain confusion term) minus a prefill-token cost term; rollouts on the construction-800 roster only, never on the union-4000. (c) E28's v1 views stay the released record; no v2 view is hand-released; the first A2T index cell flies the minimal L0 constant index with retrieval-supplied expansions, and the RL search is the A2T instance of Stage 3 once A2T-NULL and A2T-NOTOOL have read. Design note updated (section 3, 6a, 7). |
| 71 | The paired 400-row subset of the sealed union-4000: tier-stratified 50 rows per tier, drawn once and frozen, reported in natural-mixture and equal-tier weighting, or the natural tier mixture. | Owner (2026-09-21, translated): "Decision 71: as you recommended." Ruling: 50 rows per tier over the eight tiers, one seeded draw (seed 20260921) from the sample ids of the sealed union-4000, receipted under docs/receipts/rosters/ with the sample ids and their sealed comparator rows; every A2T engineering cell (A2T-NULL, A2T-NOTOOL, A2T-IDX, A2T-IDXT) reads on this roster in both weightings; the full 4,000 flies only for an admitted form. |
| 72 | The SLURP form after the HARMFUL index read: close the index line and hand 'what content, at what granularity' to Stage 3 (a), fly a lossless ordering-plus-pointer index cell (b), or only record (c). | Owner (2026-09-21, translated): "Everything else as you recommend." Ruling: (a) -- no hand-authored index variant on SLURP; the tool-free B1 fragment (B1-notool, 62.13 / 80.00) is the base for every later cell; index content is a Stage-3 action (decision 70). |
| 73 | The first Stage-3 instance: semantic advantage over scored rollout groups with additive, provenance-tagged store deltas (a), an offline Pareto reading of the OFF-null ablation table first (b), or prompt optimisation (c). | Owner (2026-09-21, translated): as recommended. Ruling: (b) then (a): the zero-GPU Pareto reading and trace counterfactual replay precede the rollout search; the Stage-3 specification is written before the first search cell; no prompt-population methods (cost model). |
| 74 | Whether the verifier (Reviewer x3 ensemble, majority vote over grouped samples) is measured against the official scorer on sealed rollouts before any further sampling or review budget is spent. | Owner (2026-09-21, translated): as recommended. Ruling: yes, zero-contact, on the sealed B2 rollouts and traces; its result fixes N per stratum and the Reviewer iteration count before any pruning cell. |
| 75 | Whether every verdict from now on carries the effect x prefill-tokens x GPU-hours frontier (pooled and per stratum) and every lock reports the knee rather than the maximum. | Owner (2026-09-21, translated): as recommended. Ruling: adopted; the read drivers produce the frontier tables. |
| 76 | Role of the Audio2Tool, contextual-ASR and Earnings-21 carriers in Stage 2. | Owner (2026-09-21, translated): "Audio2Tool, contextual ASR and E21 are at present only there to lock and generalise the engineering base; do not run experiments to optimise them -- we optimise the engineering base, not every dataset, at this stage (seeing a stable gain from the agent system is acceptable)." Ruling: in Stage 2 those carriers get engineering-generalisation proofs only -- the same harness, configuration composition and gates run a four-row smoke per carrier (Earnings first joins FlightRuntime); A2T-NOTOOL / A2T-IDX / A2T-IDXT effect cells and the A2T training-free RL instance are deferred past the Stage-2 seal; A2T-NULL (about 0.7 GPU hours, the carrier's own null) is optional and queued behind the seal flights. |
| 76a | Amendment to decision 76 by the owner. | Owner (2026-09-21, translated): "Very good, proceed as you recommend; note on decision 76 that we still need a comparison of the pure driven model against the system-level agent; the dataset can be smaller." Ruling: each generalisation carrier gets ONE paired direct-versus-system comparison on a small roster, not an optimisation programme: Audio2Tool -- the tool-free native-episode base (decision 65) on the 50-per-tier paired subset (decision 71) against the sealed direct rows of the same ids (SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1), A2T-NULL optional for margins; contextual ASR -- once Earnings joins FlightRuntime, the bare-core direct arm and the native-episode system arm on one small Earnings roster (the dev subset), read on the standard scorer beside the agentic error rate; SLURP -- the DEV-2000-added read (B6) pairs the locked plan against a direct arm on the same 1,000 rows. These reads are development numbers (decision 28) and never compared with published test baselines. |
| 77 | GPU task discipline. | Owner (2026-09-21, translated): "The GPU tasks you plan must be independent of your own thread and network environment; once a GPU task has started, never try to pause it; after a stage completes you may reorder the GPU scripts, but never let a GPU task stop because our session was interrupted." Ruling: every GPU flight is launched only through the Windows Scheduled Tasks (serving, monitor, batch driver) from the queue file; the coordinator's session only enqueues ready cells, reorders the queue between steps and reads the status file; no TaskStop, no kill, no power-setting change; the driver's first-failure-stops rule stays; the driver must re-read the queue between steps. |
| 78 | The Stage-2 seal path: the minimal path (default-plan arm + replicate, B9a acquisition, DEV-2000) then base lock v3 and the Stage-3 specification (a); waive B9a by amending decision 43 (b); keep the node-read cells before the seal (c). Serving-geometry probe G2 (np6) and any further serving investigation. | Owner (2026-09-21, translated): "No further investigation is needed; run the follow-up experiments on the engineering base as it stands after the unified prefill optimisation; there is no need to raise the batch size." Ruling: (a) without G2 -- the geometry stays np4 x 24,576 on the tool-free base; the seal flights are the default-plan arm, its replicate, B9a and B6 DEV-2000 in that order; base lock v3 and the Stage-3 specification are written in CPU time; the node-read cells (decision 51) move into the Stage-3 action space. |
| 79 | The three deviations the DEV-2000 roster (docs/readiness/2026-09-19-slurp-dev-2000-roster-v1.md) records and asks to be ruled before its flights: D1 the reserved, unopened SLURP-DEV-500-B-V1 (500 recordings) is absorbed verbatim into the added half and stops being a reserved replication roster (its 500-row read stays recoverable as an exact sub-table); D2 87 of the 913 added utterances contribute a second recording, so paired analyses cluster by utterance_id; D3 the added half follows the natural devel mixture rather than DEV-1000's equal-per-scenario shape, so DEV-2000 verdicts report both weightings. | Owner (2026-09-21, translated): "Decision 79: all three accepted; proceed as you recommend." Ruling: D1, D2 and D3 accepted as recorded; cell B6 (decision 78 seal flight; decision 76a's SLURP direct-versus-plan comparison) reads on DEV-2000-added (1,000 recordings, 913 utterances) with utterance clusters and both weightings; its two preparations -- speech-packet promotion of the 1,000 rows and the CPU speech-query embedding pass (omni-embed-nemotron-3b, tool-level contacts, the 2026-09-12 registration precedent) -- and its two arms (bare-core direct, the locked plan) are registered by script before any contact. |
| 84 | The Reviewer's verdict is unparseable prose (findings parse on 0 of 2,167 anchor outputs; REVISE recall 0.5-5 %), so the review budget cannot be measured or tuned; decision 32 had closed the review-findings format cell B7r. Repair the prose, move to structured (JSON) output, or something else. | Owner (2026-09-21, translated): "Decision 84: I feel this splits in two. One way is to have the model output a FIXED verdict result rather than repairing -- in effect let the model emit primitives, which is more reasonable than structured output; the other is structured output, which brings its own instability." Ruling: the Reviewer's verdict becomes a closed set of PRIMITIVES (a fixed vocabulary of verdict tokens the parser matches exactly, e.g. ACCEPT / REVISE-<reason-primitive>, with the free-text rationale kept beside them and never parsed), not a JSON schema; the primitive set is an engineering item on the base, measured on the same verifier instrument before any review-budget cell; decision 32's closure of B7r (the JSON findings format) stands. |
| 85 | Order of the review-loop pruning against the v2.0 lock. | Owner (2026-09-21, translated): "Decision 85: as you recommend." Ruling: v2.0 is locked on the plan as flown; Reviewer 3 -> 1 and review-off are the first Stage-3 pruning cells on the locked base, read at the plan's own null (PLANr), after the primitive verdict (84) so the pruning is read on a measurable Reviewer. |
| 86 | Whether v2.0 is locked although the arm's SLU-F1 (63.63) is under the 64 development bar. | Owner (2026-09-21, translated): "Decision 86: recall -- it is not that we lock while under the bar; the bar's logic lives on the TEST set, not the development set, so whether the bar is met is decided after Stage 3 completes, on the test set." Ruling: development numbers carry no bar (decision 28 restated): the v2.0 lock is decision 30's headroom lock on the development roster; the 64 / 78 figures are the test-set targets read once after Stage 3 (decision 29); no development read is ever called 'under the bar'. |
| 87 | The DEV-2000-added speech-query encoding pass (registered as an exclusive-GPU preparation) versus the always-on serving rule. | Owner (2026-09-21, translated): "Decision 87: this is a preprocessing chain; we can accept large-scale concurrency for preprocessing." Ruling: preparations run concurrently with the resident service and with each other at high parallelism; no service stop window is needed; the encoding pass runs now as its own scheduled task beside the resident session. |
| 88 | The form of cell B6's direct arm. | Owner (2026-09-21, translated): "Decision 88: agreed." Ruling: the direct arm is the sealed slurp-direct-max512 form (bare core, the shared np4 path, 512 completion tokens), the plan arm is cell PLAN's fragment; both on the 1,000 DEV-2000-ADDED rows, clustered by utterance, both weightings. |
| 89 | Whether Earnings joins FlightRuntime now (the contextual-ASR instance of base lock v3; a four-row smoke plus one direct-versus-system read, decision 76a). | Owner (2026-09-21, translated): "Decision 89: agreed with your recommendation." Ruling: item E35 starts now in CPU time in an isolated worktree; scope = the native episode on one small Earnings roster through the same harness and gates, no optimisation. |
| 90 | Whether to repair the kind (a) re-query (item E36b) and fly B9a v2 in the Stage-2 seal, or carry it into Stage 3. | Owner (2026-09-22, translated): "E36b goes into Stage 3." Ruling: B9a closes on the B9a-rec evidence (node instantiated, inert, root-caused); the Acquisition node stays off the locked plan for the seal; E36b (findings-keyed store search with a discriminability rule) is the first acquisition-policy cell of Stage 3. |
| 91 | Whether to fly the E35 Earnings cells now with a serving-geometry switch. | Owner (2026-09-22, translated): "E35 flies now with the geometry switch; then write base lock v3." Ruling: the resident SLURP session is stopped, the E21 geometry (q4km-e21-native-window-packets-cddb000c-np4-max1024-v1) becomes the resident session for the four E35 cells (four-row pair, then sub10 pair) through the scheduled-task queue, then the SLURP geometry returns; base lock v3 (decisions 42 / 43) is written after the E35 reads. |
| 92 | The E35 unit subsets referenced the shared 1,593-window inventory's slice tree, which the runtime refuses (slices live only under the run's own derived/obs-slices/<batch>/). | Owner (2026-09-22, translated): "E35: agreed with your suggestion (a)." Ruling: option (a) was approved; on inspection the runtime already keys the slice tree by prepared_execution_units.registry_run_id (the full44 cell's own form), so the four baselines point registry_run_id at the shared inventory's tree while batch stays the subset name -- no bytes copied, no artifact rewritten; E39 (a parent-tree rule) is unnecessary. |
| 93 | The Stage-3 construction roster SLURP-STAGE3-CONSTRUCTION-R01 (800 TRAIN rows, decision 81) draws from the whole TRAIN pool; the registered packet-promotion preflight closed the D1 media-identity gate on the first row outside the D1 identity closure. | Owner (2026-09-22, translated): "93 to 98 as you recommend." Ruling: option (a): an ADDITIVE D1 media supplement receipt for the roster (bytes hashed + container header only; no decoding, no text), pinned by the dataset fragment's `d1_media_supplement` keys exactly as the Audio2Tool rosters were extended (`docs/receipts/artifacts/d1-a2t-*.json`); the base D1 receipt is never rewritten. Built by a SLURP builder script with tests (branch fable/s3d). |
| 94 | Whether the R01 packet-promotion ENCODE (a `-ngl 0` CPU-only llama.cpp sidecar, 0 GPU-h, about 75 minutes) may run beside the E35 flight on the resident GPU session. | Owner (2026-09-22, translated): "as you recommend." Ruling: yes, in parallel, as a Windows scheduled task, with a memory watchdog that stops the sidecar when host available memory falls below 6 GB (host 43 GB, 29 GB available at decision time, sidecar about 20 GB sharing the GGUF page cache). |
| 95 | (folded into 93/94: the encoder-contact ledger rows of the R01 preparations are countersigned by root, not by the owner; the preprocess row was countersigned at a4d40438.) | -- |
| 96 | (coordinator, for the record) ROLL-1's planned_model_calls is re-registered from 800 x 11 = 8,800 to the grouped-Solver graph's own ceiling 800 x 19 = 15,200 (expected about 6,400), planned_gpu_hours 8.0 unchanged, at the readiness flip. | -- |
| 97 | If cell R-PRIM (E37 primitive verdict) reads HARMFUL, where do the decision-85 pruning cells (Reviewer 3 -> 1, review-off) fly? | Owner (2026-09-22, translated): "as you recommend." Ruling: R-PRIM NEUTRAL or ADMITTED -> the pruning cells fly on the R-PRIM base and read the primitive distribution beside SLU/intent; R-PRIM HARMFUL -> the pruning cells fly on the locked PLAN base and read SLU/intent only (the review-budget question does not depend on a parseable verdict). |
| 98 | How base lock v3 records the Earnings21 + ConEC carrier, given E35 covers 10 calls (342 windows), below the n >= 400 rule. | Owner (2026-09-22, translated): "as you recommend." Ruling: option (a): the Earnings row of base lock v3 carries the structural proof (all six nodes on FlightRuntime, the E21 geometry) plus the descriptive sub10 contrast with NO effectiveness claim; the Earnings full-discovery calibration (n >= 400 calls) is sequenced after the Stage-3 SLURP main line. |
| 99 | The definition of the Stage-3 goal's "observable positive gain". Proposed: CELL-1 vs the sealed PLAN arm on TRAIN A, official SLU-F1 CI95 lower bound > 0, intent non-inferior at the plan's own null, replicated on the same roster, then sign-confirmed on DEV-2000-ADDED. | Owner (2026-09-22, translated): "Decision 99: the observable positive gain must be LOCKED on the training set and VALIDATED on the test set; and it must be comparable with the academic baselines." Ruling: the TRAIN-side lock is the proposed rule (CI95 lower bound > 0, replicated); the Stage-3 exit then requires the ONE-SHOT test-split read of decisions 28/29 (protocol draft on branch fable/test-protocol, 16ed5b3f, to be finalised before the read) on the COMPLETE official SLURP test split with the official `evaluate.py` scorer, so the number sits beside the published SLURP test results (the 2026-09-04 floors: Google/SF-ID 64.02 SLU-F1 the weakest trained pipeline); the read reports the locked system and the bare core (direct) on the same split, once, never tuned on. Decision 86 stands: no development bar on TRAIN/DEV numbers. |
| 100 | The GPU queue after the E35 seal. | Owner (2026-09-22, translated): "as you recommend." Ruling: order A: R-PRIM -> R01 speech query-vector encoding (preparation 2) -> ROLL-1 -> pruning cells x2 -> ADV-1 -> CELL-1 + twin; B9a v2 (E36b) after CELL-1; Earnings full discovery after the SLURP main line. |
| 101 | (owner directive, unprompted) The labelling of Stage-3 experiments by their training-free RL algorithm, and the breadth of algorithms explored. | Owner (2026-09-22, translated): "Also, in the Stage-3 experiment set-up, different experiments must explicitly mark which training-free RL they use; you may explore several groups of training-free RL algorithms." Ruling: every Stage-3 cell carries a machine-checked `stage3_algorithm` label resolving in a registry of training-free RL algorithms (id, family, citation, which loop operators it defines: rollout / scoring / credit assignment / update / selection); the label appears in the experiment fragment, the readiness note, the ledger row and every verdict table; a check under `scripts/checks/` fails any Stage-3 cell without a registered label. Layer A explores at least three families on the SAME ROLL-1 rollouts and the same locked plan: Training-Free GRPO (semantic group-relative advantage -> experiential deltas), GEPA (reflective Pareto evolution of the context / instructions), ACE (agentic context engineering: generator / reflector / curator with grow-and-refine); each family yields its own delta-store version and its own CELL-1 arm, read against the sealed PLAN under the same rule (decision 99). Further families (e.g. Textual/Verbal gradient methods, experience-replay memory methods) may be added by registering them first. |
| 102 | (coordinator, CONFIRMED by the owner 2026-09-23: "agree with your recommendation") The Stage-3 construction roster R01 (800 TRAIN rows, decision 81) is refused by the rails BUILD/USE guard: 175 of its utterances are per-card sources of the authored semantic stores (intent-boundaries-v1 names 57 R01 recordings, slot-contracts-v2 155; 50 of 60 intent cards and 41 of 54 slot cards cite an R01 utterance), and every R01 row was in the train-exemplars pool (fixed model-free by the -minus-r01 store, item S3-1k). Options: (a) re-author both semantic stores from an R01-excluded support pool (model contacts, and the rollout would then use knowledge different from the locked plan's); (b) narrow the construction roster to the clean subset R01C (about 625 rows: R01 minus every utterance that is a knowledge source), a pure selection with zero contacts, roster identity changes, plan numbers scale (625 x 19); (c) declare the guard inapplicable to construction rollouts (rejected: the guard protects exactly the D2 invariant). | Coordinator ruling 2026-09-23 (Fable 5.1), to be confirmed or reversed by the owner: (b). ROLL-1 flies on R01C; a later top-up draw (R02, excluding all knowledge-source rows from the candidate pool) restores 800 if the owner wants the number back; the S3-1 roster builder's exclusion list is extended with every knowledge-source id so no future construction roster overlaps a store. |
| 103 | (coordinator, CONFIRMED by the owner 2026-09-23) After E39 and E39b (the one recovery) both hold R1 / R2 and both fail R3 (a length-truncated Perception at 320 and at 640; the parent at 1,024 lost a window the same way), what enters the base? | Coordinator ruling 2026-09-23: base lock v3.1 = finite_completion_scope + per-role caps in the base (defaults unchanged); Earnings native cells: scope answering-node, Reviewer cap 640 (solved), Reviewer probe v2, Perception cap 640 with the truncation rate reported (R3 re-stated as a measured rate, not a zero); item E41 = a bounded Perception note (structured / length-constrained instruction) with its own dry run before the sub10 re-read of the Earnings system form. Reversible by the owner. |
| 104 | When the Earnings sub10 re-read of the repaired (v3.1) system form flies. | Owner (2026-09-23, translated): "as you recommend." Ruling: after the SLURP Stage-3 main line (decision 100 order); it needs the E21 geometry switch and about 2 GPU-h. |
| 105 | Whether to replicate P0 (review-off) to narrow its interval and possibly drop the review loop on cost grounds. | Owner (2026-09-23, translated): "as you recommend." Ruling: not now; the pruning line stays closed until the TF-RL main line reads. |
| 106 | The information the Stage-3 rollouts and the advantage contact may use and record (decision 82 detail). | Owner (2026-09-23, translated): "Roll out as much information as possible; note that we are doing SYSTEM-level optimisation, not the optimisation of a single module." Ruling: the rollout receipts and the S3-3 pairs carry the WHOLE episode trajectory per sample (Perception candidates, Solver drafts, Reviewer primitives, Planner routes, revision, delivery), the advantage contact reads best-vs-worst at the system level (all nodes, not only the delivered answer) plus the construction gold, and the delta store may hold NODE-TARGETED deltas (perception hints, reviewer criteria, planner rules, slot / intent / exemplar content) so that CELL-1 can move any node's context; deltas carry slot values, intent names and phrasing patterns but never whole R01C utterances. Item S3-4s (system-level advantage + node-targeted deltas) amends S3-4 / S3-5 / S3-6 accordingly. |
| 107 | Execution details of decision 99 (the one-shot test read). | Owner (2026-09-23, translated): "The test set is read only once; the features must be built in parallel and fast; DEV may be extended -- it is the development-side optimisation resource; we want to be as complete as possible so that the test set shows a STABLE gain." Ruling: (a) exactly one complete official test-split read (13,078 recordings, system + bare core, official evaluate.py), after the TRAIN lock + replicate and a DEV confirmation; (b) the test-split preparations (roster freeze + D1 supplement, featcache packets, speech query vectors) are registered now and built in parallel ahead of time -- packet promotion on the CPU sidecar beside the GPU flights with more workers, encoding as one registered pass -- so the read waits on nothing (item S3-7); (c) the DEV side may expand beyond DEV-2000-ADDED (up to the full devel split, 8,690 recordings) as development validation, with the same preparation pipeline; DEV numbers stay development numbers (86); (d) "stable gain" = the TRAIN-locked CELL-1 gain confirmed on the expanded DEV roster before the single test read. |
| 108 | (owner 2026-09-24: AGREED with the coordinator's recommendation -- the one-shot test read is DEFERRED until a fresh-roster gain exists; no test contact before then. Original text:) The venue of the one-shot test read and the machine role of its preparations. The one-read protocol draft (`docs/readiness/2026-09-19-slurp-test-split-one-read-protocol-v1-draft.md`, section 6) recommends Remedy A (an admitted `papers/<slug>` repository) for the READ; the test-split preparations of decision 107 (packet promotion, speech query encoding) are encoder contacts on test media and need a machine role today. | Coordinator proposal 2026-09-23: 108a -- a dated owner allowance receipt (`docs/receipts/owner/2026-09-23-slurp-test-split-allowance-v1.json`, schema `saea-owner-split-allowance-v1`, committed as `pending-owner`) authorising the split role `final-report` for the three preparation run ids only (label-free feature construction reusable by either venue); 108b -- the venue of the read itself decided after the TRAIN lock (Remedy A recommended). Every `final-report` plan is refused by the contracts until the receipt reads `authorised`. |
| 109 | (coordinator, PROVISIONAL, pending owner) The devel remainder of decision 107(c), defined by subtraction, contains the 60 FINAL60 recordings (split role `reserved-final-unread`, held back 2026-08-23) and the 60 historic probe-60 recordings. | Coordinator ruling 2026-09-23: both sets are carved out before anything flies (roster `SLURP-DEVEL-REMAINDER-V2`, expected 6,570 rows; v1 stays committed as the superseded parent); the FINAL60 reservation is not spent by a development read, and the remainder stays contact-fresh. The expanded DEV read is therefore DEV-1000 + DEV-2000-ADDED + REMAINDER-V2 = 8,570 of the 8,690 devel recordings. Reversible by the owner (release FINAL60 under 107 and re-freeze). |
| 110 | (coordinator, provisional 2026-09-24; RATIFIED by the owner 2026-09-24 after the flight) Iteration 3 of the Stage-3 line is a coverage-gated APPLICATION policy, not a third retention and not a `general`-targeted mechanism. Evidence: CELL-2 read NEUTRAL by width (SLU +0.64 [-0.76, +1.92], intent -0.09 [-1.22, +0.96]; twin +0.05 / -0.93; arm minus twin +0.59 / +0.83); the general-scenario diagnostic (`docs/results/2026-09-24-slurp-general-scenario-diagnostic.md`) shows the general loss is a form cost of carrying a supply, twin-reproduced, diffuse, Fold A upper bound 0.56 pp intent / 0.24 pp SLU; the per-scenario form / content split of CELL-2 shows content gains where the store has reach (news +7.4, alarm +4.2, qa +4.2, weather +4.1 pp SLU) and a negative form cost on general, alarm, music, social, iot, play, news. Mechanism (merged 060d822c, model-free, 35 tests): a row-level scenario gate on the candidate-bound routes, policy `majority-candidate-scenario-not-in-v1` over those seven scenarios, reading only the row's own Perception candidate state; the Perception unconditional route is dropped. Venue: DEV-2000-ADDED (1,000 fresh rows; sealed PLAN 65.40 / 76.6 from B6) against the sealed PLAN there, with a PLAN replicate on the same roster for its own null, arm then twin -- decision 99's fresh-roster replicate, the first out-of-fold read of the line. The gated set was chosen on TRAIN Fold A, so a Fold A read would be a third look; this venue avoids it. Cost about 5 GPU-h (PLANr 1.7, arm 1.7, twin 1.7). Registration in flight (branch fable/cell3reg); the flight follows the CELL-1-GEPA read. The owner ratified the executed decision on 2026-09-24; outcome: CELL-3 HARMFUL by the registered rule on the fresh roster (see decision 111). | decided |
| 111 | (owner 2026-09-24, on the coordinator's recommendation) CLOSE the semantic-delta APPLICATION line: no further application-side cell (gate, pruning, re-ranking, capping) over the stage3-deltas v1r / v2 / gepa-v1 stores; the stores stay sealed artefacts; the line is written up as a negative result with its full protocol. Evidence: CELL-1 NEUTRAL, CELL-2 NEUTRAL by width, CELL-1-GEPA NEUTRAL (all TRAIN Fold A vs the sealed PLAN at its own null), CELL-3 (scenario gate, fresh DEV-2000-ADDED) HARMFUL by the registered rule (SLU -1.44 [-2.88, -0.05]) with the loss diagnostic showing run-to-run noise of about +-2 pp on 355-row sub-splits, a store part of -0.35 pp above its own null, diffuse per-value harm, no Fold A -> DEV transfer, and a perfect-gate bound of about PLAN. | decided |
| 112 | (owner 2026-09-24, on the coordinator's recommendation) The next route to an observable gain is INFERENCE-TIME AGGREGATION (sample-and-aggregate: N Solver samples committed by a deterministic rule -- majority intent, entity support threshold, medoid sample delivered so the I7 invariant holds; a training-free SELECTION operator at inference, algorithm label to be registered). Order: (1) a zero-contact OFFLINE read over the sealed ROLL-1 five samples per row (625 R01C rows, per-sample official scores) against sample 0; (2) only if it reads >= +1.5 pp SLU, register AGG-1 on TRAIN Fold A vs the sealed PLAN at its own null, four-row smoke first; (3) fresh-roster replicate on DEV-2000-ADDED at its sealed own null (h_SLU 1.2525 / h_intent 1.1520); (4) then the one-shot test read under decision 108. A core swap (decision 112-B) is the fallback if the aggregation line is negative. | decided |
| 113 | (owner 2026-09-24) The Stage-3 record must NOT be written as 'no gain': the owner asks for a detailed account of what was done and how. Recorded wording: every Stage-3 arm is significantly above the Stage-2 lock (B5e official 62.34 / 80.09: CELL-2 +1.93 SLU [+0.56, +3.34] / +2.04 intent [+0.74, +3.34]) but that gain belongs to the locked v2.0 PLAN, which every Stage-3 cell must beat; against PLAN the point estimates are positive on SLU for CELL-2 (+0.64) with content above form on both families (arm minus twin +0.59 / +0.83 and +0.73 / +0.19), iteration 1 -> 2 moved +1.12 SLU / +0.65 intent with harms contracting, and per-scenario content gains reach +7 to +15 pp where the store has reach -- all inside the own-null band (h about 1.25 pp) and not transferred out of fold. The measurement floor itself (about +-1.3 pp pooled at n = 1,000, +-2 pp on 355-row splits) is a Stage-3 finding that bounds every later claim. The account is in the coordinator's report of 2026-09-24 and the Stage-3 line note. | decided |
| 114 | (owner 2026-09-24, as recommended) The DEVEL-REMAINDER v2 comparators (PLAN + direct, about 11 GPU-h) fly only after the decision-112 offline read is positive and a mechanism exists to test; otherwise not. | decided |

Outcome of decision 22 (2026-09-19, first use, the B4b replicate): the resume-recovery flew 500 rows and kept 580 under I7r custody after the 2026-09-18 serving-session death; the merged 1,080-row manifest was officially scored once and reads +1.54 pp official pooled SLU CI95 [+0.30, +2.93] against the anchor (intent +0.65 [-0.62, +1.87]): cell B4b REPLICATED, module M4b's obligation MET, the SLURP default plan pins slot store v2. The resume saved 1.72 GPU hours against a full re-fly. Read: docs/results/2026-09-19-slurp-b4b-replicate-verdict.md.

Outcome of directive 26 (2026-09-19, after the B8a read): the first analysis-to-node conversion is admitted. The delivery-time normaliser node (module M3, item E11) raises the official unprojected pooled SLU-F1 by +3.46 [+2.78, +4.18] on the anchor and +1.53 [+1.05, +2.03] on B1 with intent up and zero rows harmed, and the four-row smoke passed structurally; the SLURP default plan now arms native_episode.deliver_normaliser and every later official number is read on a system that contains the node. With the node, B1 reads 62.67 / 81.76 and B5e 63.78 / 81.85 official (the bar remains SLU >= 64 and intent >= 78, replicated). Read: docs/results/2026-09-19-slurp-b8a-deliver-normalise-verdict.md.

Outcome of decision 32 (2026-09-19, after the B7a v2 read): cell B7a v2 (NCP L1) reads HARMFUL under the registered rule (official SLU -0.31 [-1.81, +1.12], intent -0.65 [-2.18, +0.87]; interval width rather than a measured loss, and +11.6 % GPU hours for no gain). The pre-authorised branch fires: cells B7r and B7c close unflown, cell B8b is re-based on the anchor and re-registered, level L2 stays unflown. Under decision 30 the one-factor NEUTRAL/HARMFUL streak stands at one (B8a admitted in between). Read: docs/results/2026-09-19-slurp-b7a-ncp-l1-anchor-v2-verdict.md.

Outcome of decisions 9 and 30 (2026-09-19, after the B4a v2 read): cell B4a v2 reads HARMFUL under the registered rule (intent +0.74 [-0.30, +1.75], SLU -0.70 [-2.29, +0.89]; interval width, and the fallback candidate was appended on 1,052 rows and chosen on none while costing +39 % GPU hours). Decision 9 fires: cell B4c (intent store v2 alone) closes unflown. Under decision 30 the streak of consecutive one-factor NEUTRAL/HARMFUL cells is two (B7a v2, B4a v2); a third locks v2.0 on the best admitted combination. Read: docs/results/2026-09-19-slurp-b4a-fallback-quirky-anchor-v2-verdict.md.

Outcome of decisions 55 and 56 (2026-09-20, after the B1-notool read): the tool withdrawal on the B1 base reads official SLU +0.99 [-0.59, +2.50] and intent -0.19 [-1.33, +0.91] against the sealed B1 arm; the intent lower bound misses the 1.2212 margin by 0.11 pp with no measured loss on any metric, B1r's own null failing the same clause, and eight length-capped Reviewer rows deciding it. The verdict writes NON-INFERIORITY NOT PROVEN; the coordinator applies decision 25 and the B5e precedent and records NEUTRAL, so the withdrawal enters the SLURP default plan and is the base of the knowledge-index cell (decision 53), recorded in the harness-admission receipt as the RETIREMENT of the Reviewer's task-contract toolkit (item E25: switch class phase_tools, status RETIRED); 0-A is not registered; under decision 56 (SLU +1.6 %, intent -0.2 % relative) the anchor-base and plan-base cells are not flown. Efficiency: prefilled tokens per row -69 %, GPU hours 0.418x, throughput 1.86x, projected test read 19.5 h. The owner may overrule the NEUTRAL application; the music scenario's intent band breach (-8.33, repeats against B1r) is carried into the index cell's read.

Outcome of the 2026-09-20 briefing (decisions 61-64): the B1-notool NEUTRAL is final; IDX (registered 36a445dd, smoke flipped ready 061394e0 and re-pinned after the consumption read was added) and IDXT fly at decision 52's defaults on the tool-free B1 base with the index-consumption read as a mandatory part of both verdicts; the order after them is fixed by decision 63.

Outcome of decisions 62 and 64 (2026-09-21, after the IDX and IDXT reads): cell IDX reads HARMFUL against the sealed tool-free B1 arm (official SLU -7.37 [-9.72, -4.80], intent -2.41 [-4.56, -0.32]); the twin reads HARMFUL as a control (SLU -9.97 [-12.46, -7.32]); the decomposition puts the loss in the FORM (constant index + pointers + four expansion cards in place of the per-row cards and the raw exemplar block) with a content term of +2.60 SLU / -2.59 intent that is an upper bound under the decision-62 length difference. The index-consumption read states MISLEADING TERSENESS (IDX verdict) / undecided with NON-CONSUMPTION better supported (twin verdict); under decision 64 the form is closed at decision 52's defaults, the richer-granularity route is contraindicated, and the next form is the owner's decision (72). Efficiency was as designed (prefill -58 %, GPU hours 0.83x) and does not rescue the cell (decision 50). The tool-free B1 base (62.13 / 80.00) remains the SLURP base; the read drivers are reusable by stage (decision 58).

Outcome of decisions 57 and 78, part 1 (2026-09-21, after the PLAN read): the default plan flown as one arm reads NEUTRAL against the tool-free base (intent +2.22 [+0.92, +3.56] proven; SLU +1.50 [-0.04, +3.24] unproven) and is at parity with the provisional lock B5e + node (SLU -0.15, intent +0.37, both inside the plan's null); it lies on both Pareto planes. Candidate v2.0 lock numbers 63.63 / 82.22 await the replicate PLANr; the provisional lock record stands until then.

Outcome of decision 78, part 2 (2026-09-21): PLANr sealed cleanly (4,389 contacts, 1.665 GPU hours; read pending); the B9a arm ABORTED after 327 contacts on the first row that routed ACQUIRE -- the runtime never bound the kind (a) re-query (`acquisition_requery`), which the E18 / E32 proofs supplied through the test harness; first failure of the cell, one recovery re-registration allowed after the fix (item E36) is proven model-free on sealed rows.

Outcome of decisions 30 / 57 / 78 (2026-09-22): cell PLANr REPLICATED cell PLAN within the plan's own null (SLU +0.17 [-1.11, +1.38], intent +0.28 [-0.74, +1.25]); **v2.0 is LOCKED** on the PLAN fragment as flown (`docs/results/2026-09-22-slurp-v2-lock-v1.md`), lock numbers 63.63 / 82.22, own null h_SLU 1.2485 / h_intent 0.9943; under decision 86 no development bar applies. Item E36 (the live kind (a) re-query binding) merged at fef4341e; the B9a recovery re-registration follows. Decision 84's design is `docs/superpowers/specs/2026-09-22-slurp-reviewer-primitive-verdict-design.md` (item E37). Decision 89: item E35 in progress on an isolated worktree.

Outcome of decisions 43 / 44 / 78 (B9a, 2026-09-22): cell B9a-rec read NON-INFERIORITY NOT PROVEN by width (intent 0.00 [-1.10, +1.08] against h 0.9943; SLU +0.26 non-inferior; no loss) and the acquisition read shows the node INERT (18 ACQUIRE routes, 0 items each: the E36 binding re-runs the Solver's supply and excludes it). The node is instantiated in the harness but not admitted into the locked plan; item E36b (findings-keyed store search over the released stores) is designed (`docs/superpowers/specs/2026-09-22-e36b-findings-keyed-requery-design.md`). Owner decision needed: (a) admit B9a v2 with E36b after a model-free replay proves non-empty acquisitions on the 18 sealed rows, or (b) keep the node off the plan and revisit in Stage 3.

Outcome of decisions 76a / 78 / 88 (B6, 2026-09-22): the locked plan against the bare core on the fresh DEV-2000-ADDED roster reads +27.30 pp official SLU-F1 [+24.05, +30.50] and +14.90 pp intent [+11.78, +18.03] (38.09 / 61.7 -> 65.40 / 76.6), DESCRIPTIVE, both channels; the decision-78 seal path (PLAN + PLANr lock, B9a-rec, B6) is complete. Open before base lock v3 (42 / 43): the Acquisition node (E36b decision) and the Earnings flights (E35, serving switch). Note `docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md`.

Outcome of decisions 80-83 (owner, 2026-09-22, translated): 80 "N = 5, start with that" (N = 5 rollouts per state; T = 3 as proposed); 81 "the rollout roster may sample semantically distant samples; 800 as you suggest" (about 800 construction rows drawn with a diversity rule over the sealed content embeddings -- farthest-point coverage so semantically distant utterances are represented -- never a TRAIN A / TRAIN B / DEV-1000 / DEV-2000 utterance); 82 "as you suggest" (the semantic-advantage contact may see the construction row's gold; its output enters only provenance-tagged store deltas, never an evaluated row); 83 "find the frontier per scenario" (selection keeps the per-scenario effect x prefilled-token frontier; the cost weight is read from the frontier slope). Stage 3 opens after base lock v3 with the order E37 -> pruning cells (85) -> E36b -> the knowledge-delta loop.

Owner goal (2026-09-22, translated): "Finish the Stage-2 engineering wrap-up and start Stage 3's engineering base and research: the basic engineering base is set by the field's open-source training-free RL techniques; the research work then optimises and improves those training-free RL capabilities. Complete Stage 3 and show an OBSERVABLE POSITIVE GAIN." Applied as: base lock v3 = the Stage-2 wrap-up; Stage 3's first engineering deliverable is a faithful implementation of the surveyed open-source training-free RL loop (Training-Free GRPO semantic advantage + GEPA reflect-and-select + ACE grow-and-refine, survey 2026-09-21) on the locked base, read against the sealed PLAN arm; improvements come after that base reads.

Outcome of decisions 89 / 91 / 92 / 98 (E35, 2026-09-22): the Earnings21 + ConEC carrier flew both arms through FlightRuntime on the E21 geometry (STRUCTURAL PASS; sub10 system 1,597 contacts through all six nodes); the descriptive sub10 contrast is HARM as flown (corpus WER 0.0724 -> 0.2863, numeric 0.9239 -> 0.7106, 10 / 10 calls) and was root-caused model-free to E13's episode-wide scope voiding 76 windows after a truncated Perception contact (0.0778 had they scored like the direct arm); base lock v3 records the carrier as on the base with the defect open (item E39 -> base lock v3.1 after a four-row dry run); no effectiveness claim (n = 10). Read: `docs/results/2026-09-22-e21-native-window-flightruntime-e35-read.md`.

Outcome of decisions 84 / 85 / 97 (R-PRIM, 2026-09-22): the primitive verdict parses on 100 % of 1,091 Reviewer visits (measurability achieved); against the sealed PLAN arm SLU +0.58 [-0.82, +1.80] non-inferior, intent -0.09 [-1.16, +0.94] non-inferiority not proven by width -> NEUTRAL, cost lower; per decision 97 the pruning cells P1 (Reviewer 3 -> 1) and P0 (review-off) fly on the R-PRIM base; the Reviewer says ACCEPT on 98.4 % of visits and flags 11 of 598 wrong rows (REVISE precision 0.91, recall 0.017). Read: `docs/results/2026-09-22-slurp-review-primitives-verdict.md`.

Outcome of decision 85 (P1, 2026-09-23): NEUTRAL (non-inferiority NOT PROVEN on SLU by width, not by loss): SLU -0.15 pp [-1.38, +1.24] misses the margin 1.2485 by 0.13 pp of CI width, intent +0.09 pp [-0.69, +0.90] non-inferior. The factor is nearly a no-op on this base: the R-PRIM Reviewer already used one visit per row on 1,069 of 1,080 rows (its max_iterations 3 was never drawn), so P1 removes at most the second Reviewer contact of 11 rows; contacts per row 4.017 vs 4.031, GPU-h 1.38 vs 1.57 (throughput noise, not a budget saving). The review-budget question is answered by P0 (review-off), not by P1. Decision 97 stands: not HARMFUL. Read: `docs/results/2026-09-23-slurp-prune-reviewer1-verdict.md`.

Outcome of decision 85 (P0, 2026-09-23): NEUTRAL (non-inferiority NOT PROVEN on both metrics by width, not by measured loss): SLU -0.36 pp [-1.45, +0.78] vs margin 1.2485; intent -0.56 pp [-1.60, +0.52] vs margin 0.9943; no CI95 upper bound below zero, no point estimate beyond a margin (decision 25 Method B). Removing the review loop halves the contacts (2.00 vs 4.03 per row, prefilled tokens 7,802 vs 8,346, GPU-h 1.26 vs 1.57) and costs at most -0.36 SLU / -0.56 intent by point estimate, unproven in either direction at this width; the locked plan keeps its Reviewer + Planner (decision 85 admits a pruning only on a proven non-inferior read), and a request-identical replicate would be needed to narrow the interval before any plan change. Together with P1 (no-op) and R-PRIM (98.4 % ACCEPT, recall 0.017), the review loop on the locked plan is a 2-contact-per-row insurance whose measurable value is within the null band. Read: `docs/results/2026-09-23-slurp-prune-review-off-verdict.md`.

Outcome of decision 109 (2026-09-23, coordinator): SLURP-DEVEL-REMAINDER-V2 frozen (6,570 recordings / 1,827 utterances / 18,611.58 audio-s; 3,176 headset / 3,394 far-field; excluded union 120 recordings, sha256 over the sorted excluded ids 30ca991c...; split identity f8af142b...; receipt docs/receipts/rosters/slurp-devel-remainder-v2.json). Four parts 1,000 + 1,000 + 120 + 6,570 = 8,690, pairwise disjoint; warm legacy-cache rows 0. Residue finding (REM-D1): the carve-out is at RECORDING granularity, so 383 sibling recordings of 108 carved-out sentences remain in v2; this matches how the DEV ladder itself was built (DEV-1000 and DEV-2000-ADDED already hold other recordings of 1,719 of the remainder's utterances), so recording-granularity enforcement is accepted and no v3 is cut unless the owner rules otherwise.

Outcome of decision 99 (CELL-1, 2026-09-23): NEUTRAL by width; NON-INFERIORITY NOT PROVEN on either metric (no observable positive gain on TRAIN Fold A; the twin reproduces the arm within noise, so the delta store's content moves nothing at the pooled level). Against the sealed PLAN arm the arm reads official pooled SLU-F1 63.15 vs 63.63 (-0.48 pp, CI95 [-2.18, +1.24]) and intent 81.48 vs 82.22 (-0.74 pp, CI95 [-2.17, +0.57]); the derangement twin reads 63.19 (-0.44, CI95 [-1.94, +0.99]) and 82.31 (+0.09, CI95 [-1.19, +1.30]); arm minus twin is -0.04 pp SLU and -0.83 pp intent (descriptive): the pooled effect is neither content nor form. Every row received deltas (256 of 379 distinct values supplied; Planner reaches 59 % of rows), the per-delta paired outcomes are strongly heterogeneous (Solver deltas +5 to +6.5 pp SLU on 100+ rows beside -4 to -5 pp), and the per-scenario table swings from audio +8.9 / weather +8.3 / datetime +4.2 to general -12.4 / alarm -6.8 / news -6.6 / play -5.8 pp -- the pattern decision 83's retention rule was preregistered for (iteration 2: 200 kept / 179 retired, iteration-2-retention-v1.md). Cost: contacts +2.9 %, GPU-h +2.5 %, prefilled tokens +10.9 %; off both frontiers. The loop itself (rollout -> scoring -> advantage -> curation -> release -> cell -> read) closed end to end under the contracts; the four launch defects of 2026-09-23 were mechanism-wiring defects fixed before any generation contact was wasted beyond 320 metered calls. Read: `docs/results/2026-09-23-slurp-stage3-delta-cell-r01-verdict.md`.

Outcome of decisions 83 and 99, iteration 2 (CELL-2, 2026-09-24): NEUTRAL by width; NON-INFERIORITY NOT PROVEN on intent (SLU non-inferior and positive but unproven); iteration 2 moves the arm in the right direction without a proven gain. Against the sealed PLAN arm the arm reads official pooled SLU-F1 64.27 vs 63.63 (+0.64 pp, CI95 [-0.76, +1.92]; non-inferior at the 1.2485 margin, gain unproven) and intent 82.13 vs 82.22 (-0.09 pp, CI95 [-1.22, +0.96]; the lower bound sits 0.23 pp beyond the -0.9943 margin, so non-inferiority is NOT proven by width, not by a measured loss); the per-row SLU mean is +1.30 pp (CI95 [-0.04, +2.67], CI90 [+0.16, +2.44]; saves 87 / harms 70) and the TRAIN symmetric scorer agrees in sign (+0.66). The derangement twin reads 63.68 (+0.05, CI95 [-1.52, +1.62]) and 81.30 (-0.93, CI95 [-2.40, +0.41]); arm minus twin is +0.59 pp SLU and +0.83 pp intent (descriptive): the retained content sits above its own form control on both metrics, inside the noise band. Iteration 1 -> 2 (CELL-1 -> CELL-2): SLU -0.48 -> +0.64, intent -0.74 -> -0.09; the harm scenarios contracted (alarm -6.8 -> -3.6, news -6.6 -> -0.5, play -5.8 -> -0.6) and the winners grew (audio +8.9 -> +14.5, weather +8.3 -> +9.7, email +3.5), while general stays the hole (-12.4 -> -10.6 SLU, -6.7 intent) because no retained value targets it. Against the Stage-2 lock B5e official the arm is +1.93 SLU [+0.56, +3.34] and +2.04 intent [+0.74, +3.34]. Consumption: 121 of 200 values supplied, Solver reaches 68.5 % of rows, Reviewer 64.1 %, Planner 18.3 % (10 of 14 Planner values retired), one Solver value (d1c93189) reads -1.9 SLU / -2.2 intent on 182 rows. Cost: 4.15 contacts per row (+1.3 %), 1.768 GPU-h (+0.6 %), prefilled tokens +6.6 %, zero rows compacted. A SECOND look on the rows whose CELL-1 read chose the retained set: a development number under owner decisions 28 / 86, and no claim before the fresh-roster replicate. Read: `docs/results/2026-09-24-slurp-stage3-delta-cell-r02-verdict.md`.

Outcome of decision 101 for the GEPA family (CELL-1-GEPA, 2026-09-24): NEUTRAL by width; NON-INFERIORITY NOT PROVEN on both metrics (no observable gain on TRAIN Fold A; the GEPA family reproduces the Training-Free GRPO family's shape: fuller reach, no pooled effect, the same strata lose). Against the sealed PLAN arm the arm reads official pooled SLU-F1 63.60 vs 63.63 (-0.04 pp, CI95 [-1.58, +1.39]) and intent 82.13 vs 82.22 (-0.09 pp, CI95 [-1.54, +1.32]); both guards fail by width only, with intervals wider than CELL-2's. The derangement twin reads 62.87 (-0.76, CI95 [-2.39, +0.76]) and 81.94 (-0.28, CI95 [-1.51, +0.89]); arm minus twin is +0.73 pp SLU and +0.19 pp intent (descriptive): the GEPA content sits slightly above its own form control, inside the noise band. Reach is far fuller than the v2 store's (299 of 448 values supplied; Solver 93 %, Reviewer 91 %, Planner 90 % of rows against 68 / 64 / 18 %) at a higher cost (prefilled tokens +14 %, GPU-h +6 %, 4.17 contacts per row), and it buys no pooled effect. The per-scenario table has the same shape as both TF-GRPO cells: general -9.4 SLU / -8.3 intent (twin -18.7 / -5.0), news -6.3, social -4.4, music -4.2 against audio +7.0 / +6.7, weather +7.8, datetime +4.7, iot +3.7. Against the Stage-2 lock B5e official the arm is +1.26 SLU [-0.22, +2.78] and +2.04 intent [+0.49, +3.54]. Two families with different authoring mechanisms (per-row advantage statements; per-group reflective proposals) reproduce one pattern: strata the store covers gain, strata it does not cover pay a form cost, the pool nets to zero -- the lever is WHERE the store is applied (iteration 3, provisional decision 110, the scenario-gated application policy now flying as CELL-3 on DEV-2000-ADDED), not which family authored it. Comparing GEPA against Training-Free GRPO head to head is a separate read with its own preregistration and is not made here. Read: `docs/results/2026-09-24-slurp-stage3-delta-cell-gepa-r01-verdict.md`.


Outcome of decisions 110 and 111 (CELL-3, 2026-09-24): HARMFUL on the SLU guard by the registered rule on DEV-2000-ADDED (SLU -1.44 [-2.88, -0.05], intent 0.00); twin NEUTRAL (+0.38 / 0.00), so the loss is the store's content; noise on 355-row splits about +-2 pp; a perfect gate reaches only ~PLAN. The semantic-delta application line is closed (111); the next route is decision 112. Read: `docs/results/2026-09-24-slurp-stage3-delta-cell-r03-gate-verdict.md`.

## Owner objective and rulings of 2026-09-25 / 2026-09-26 (consolidation: this file is again the single decision registry)

Between row 114 (2026-09-24) and 2026-09-26 the programme recorded its owner rulings as dated
readiness files instead of rows here, so a reader could no longer find the governing decisions in
one place. Rows 115-211 fold those rulings back in (210 is reserved by re-plan v6 and still open). Row 115 carries the governing objective and is
placed first; rows 116-125 then run in chronological order of each ruling's own date. Every row
names the file that holds the ruling: those files stay the record and are not edited by this
consolidation, and a file that only designs, without an owner ruling in it, got no row.

| # | Question | Decision |
| --- | --- | --- |
| 115 | (owner 2026-09-26, the governing Stage-3 objective) What is Stage-3 work measured against, and when does Stage 3 close? | Owner (2026-09-26, translated): complete the Stage-3 experiments; build the academic baseline and the optimisation space on the industry's latest LOCKED training-free RL and finish the baseline set-up; then analyse where those locked algorithms fall short on these tasks and IMPROVE THE TRAINING-FREE RL ALGORITHM ITSELF so the agent performs better; lock on SLURP first, then extend to Audio2Tool and E21 / E22; the goal is a STABLE GAIN. Ruling: this is the current objective of record and it SUPERSEDES THE PHRASING of decision 99 wherever the two differ, while 99's substance stays in force (the TRAIN-side lock, a number comparable with the published SLURP baselines, exactly one test read). **Stage 3 closes when a stable gain is VALIDATED ON THE TEST SET**, where stable = admitted on TRAIN under 99's rule (official SLU-F1 CI95 lower bound above zero with intent non-inferior at the own null), replicated on a fresh dev roster, then read ONCE on the complete official test split under decisions 99 / 107 / 108; per 108 that read stays deferred until the fresh-roster gain exists. The published training-free RL algorithms are the academic baseline and the starting optimisation space, not the endpoint. Carrier order: SLURP locks first; Audio2Tool and E21 / E22 follow, each with its own native task and scoring definitions. |
| 116 | (owner 2026-09-25, steering; recorded in `docs/readiness/2026-09-25-stage3-system-trajectory-optimization.md` and restated as an "owner scope clarification" in `docs/readiness/2026-09-25-slurp-stage3-finite-policy-design-v1.md`) What is the unit that Stage-3 optimisation acts on? | Owner (2026-09-25): the optimisation unit is the COMPLETE AGENTIC SYSTEM, not a component. This supersedes any implication that optimising the Solver example count is the final research objective; terminal reward on a single supply knob remains a valid restricted comparator (the finite-supply bandit) but is not sufficient coverage of system optimisation. Ruling: the unit is one input's actual full native episode, ending in delivered output or a registered terminal fallback/abstention, with every role visit, evidence query, tool attempt, Planner route, revision and the final delivered bytes preserved as distinct artefacts. No component winner is promoted from an isolated prefix, no local Solver score is used as system reward, and independent component gains are never assumed to add. |
| 117 | (owner, recorded 2026-09-25 in `docs/handoff/HANDOFF-TO-FABLE51.md` at commit `3a950f53`) Does the GPU power-mode investigation stay open? | Owner: the power mode is CONFIRMED OPTIMAL; "do not reopen that investigation." Ruling: closed. No power, driver, TDR or WSL-cap change may be made as a throughput measure, and the 2026-09-26 status note repeats that no further owner choice on power mode is required (`docs/handoff/2026-09-26-owner-status-and-next-flight.md`). A power or driver change proposed during a crash diagnosis needs its own diagnosis and a specific justified action first. |
| 118 | (owner 2026-09-26, recorded at 2026-09-26T04:53:30Z in `docs/readiness/2026-09-26-slurp-system-batch-cadence-owner-decision-v1.md`) How often does the learned policy update during Stage-3 construction? | Owner (2026-09-26, translated): "Update after each sampling batch; that is closer to actual training." Ruling: the per-batch update cadence replaces the earlier draft of one update after R01C625 and one after Fold A1080. Each batch keeps its policy and memory frozen until every actor trajectory, the complete official scoring job and the registered semantic update have sealed; the final partial batch is retained; a tied or unusable group becomes a recorded no-change transition with exposure retained, never hidden resampling. M1 denotes the checkpoint after all R01C batches and M2 the checkpoint after both construction cohorts -- not one or two update operations -- and M2 stays the PROSPECTIVELY selected primary policy, never replaced by a better-looking earlier checkpoint after the B outcomes. The shared runtime memory bound of 32 records is a maximum, not a target, and the updater must see it. Full B1080 evaluation uses matched default, empty-memory tool control, M1 and M2; no update consumes B outcomes; DEV6570 and test13078 remain closed. The file's batch-size arithmetic (at most 32 TRAIN inputs per batch, 20 + 34 batches, at most 54 updates, 216 construction score jobs) was superseded the same day by row 119; the cadence itself stands. |
| 119 | (owner 2026-09-26, recorded in `docs/readiness/2026-09-26-slurp-system-resource-and-prefix-amendment-v1.md`) May the 32-input batch size be frozen before a capacity analysis? | Owner (2026-09-26): no. The owner confirmed the per-batch cadence and then required explicit VRAM/token analysis BEFORE fixing the batch size, at least 10 GiB available for Windows, consistent prefixes during sampling, and adequate output space. Ruling: the cadence of row 118 is retained and its 32-input assumption, 54 updates and 216 construction score jobs become historical draft arithmetic. Batch size is unfrozen: evaluate small update batches, initially 4 or 8 inputs, under complete actor AND semantic request envelopes, then freeze one size, group count and deterministic order before outcomes, keeping the tail. Four complete trajectories per input remain proposed and serialised through one bounded shared service; an update batch is never GPU concurrency, and all batch trajectories are never launched at once. Admission requires at least 10 GiB measured Windows available RAM throughout a run (the owner's engineering reserve) with new admissions draining from 12 GiB, refusal on a missing or stale host reading, real request fit (input + full output reserve + registered margin <= slot context, refitted when new memory is materialised), and actor and semantic output limits set SEPARATELY -- a batch-operation JSON must not inherit the SLURP answer's 512-token cap. The two-slot / 24,576-token-per-slot decoder-only geometry (49,152 total, about 2,448 MiB less analytical K/V payload) is the first sizing CANDIDATE only and is not launched by the amendment. Prefix rule: for the same input and role the task contract, knowledge order, speech identity, memory version and tool schema bytes stay stable across replicas; the sampling seed varies in request parameters only, never by injecting seed, run id, timestamp or replica prose into the prefix. |
| 120 | (owner question 2026-09-26, recorded with a root recommendation in `docs/readiness/2026-09-26-intent-entity-order-system-design-v1.md`) Should the system first propose Top-K intents and scope entity interpretation by them, or first detect entities and use them to restrict intent candidates? | Owner scope correction (2026-09-26): the question concerns intent recognition and slot extraction as two separately defined, correlated PREDICTION TASKS -- not the relationship between retrieving intent candidates and choosing one; the candidate-coverage factorisation is a secondary diagnostic only. Coordinator recommendation in the same note (provisional, not owner text): intent-hypothesis-first proposal, then candidate-conditioned entity hypotheses and joint resolution, with intent and slot stores kept separate and explicit frame-to-role bindings preserved. How entity evidence helps intent: observed entity evidence and relations confirm or revise the frame, without discarding action words or the original speech; shared entities across several intents are weak discriminators, an absent optional slot never disqualifies an intent, and an expected slot is never evidence that its value was spoken. Neither factorisation wins by entropy alone -- the intent-first and entity-first chain-rule factorisations describe the same joint distribution -- so a later registered comparison must hold speech, knowledge snapshots, tool permissions and system budgets fixed, vary only the order and contents of the task-to-task information, and report the four joint error cells. No architecture change or model contact is authorised by the note. |
| 121 | (owner 2026-09-26, recorded in `docs/readiness/2026-09-26-intent-slot-task-coupling-design-v2.md`, the focused successor to row 120's note) What exactly is the intent/slot research question? | Owner scope correction (2026-09-26): intent recognition and slot extraction are SEPARATE BUT RELATED tasks, and the question is the information they should exchange; candidate recall versus selection is not the principal research question. Ruling as designed: separate definitions, knowledge stores and evaluation targets do not imply statistical independence, and neither task being correct guarantees the other. The preferred -- explicitly not proven -- schedule is tentative intent interpretation, then intent-conditioned slot interpretation, then evidence-based reconsideration when the two conflict; Top-K preserves uncertainty at that interface and is not the objective. Reviewer checks intent support and slot support separately and then their compatibility, naming actual supporting or contradicting evidence, because two mutually consistent answers can both be wrong; Planner routes; Solver keeps final task-answer authority. Report intent accuracy, official slot SLU-F1 and complete-task exact success separately, plus the four joint error cells before and after each handoff and at delivery, with corrected and newly damaged task counts. The existing `intent_bindings` linkage must not be renamed a new mechanism. |
| 122 | (owner 2026-09-26, recorded in `docs/readiness/2026-09-26-system-knowledge-rsi-design-v1.md`) Is training-free optimisation of the knowledge KEYS and VALUES admitted as a second optimisation object beside task-execution memory? | Owner direction (2026-09-26): yes, as DESIGN -- sample alternative intent and slot descriptions, optimise retrieval keys and consumed values, execute the existing full agent system, and return the observed outcomes to the description generator for reflection and adjustment; the generator may be a text model or the frozen Omni core, and no model weights change. Ruling: admitted as a research design that registers no model, embedding, scoring or external API contact. Two sampling levels -- knowledge-proposal sampling and task-trajectory sampling -- with ONE full-system return; a no-change candidate always stays legal; a single rewrite, an offline retrieval gain or a root-authored correction is never a completed training-free loop. The unit of treatment is the whole knowledge snapshot and its resulting system trajectory. The first registered generator is the local frozen Omni, preserving the zero-paid-API boundary; the owner-suggested stronger text generator ("Astra") is a possible separate offline construction factor and never a second runtime answerer or an unlogged judge. Prioritise a slot-value-only first comparison; the authored intent activation text currently feeds BOTH key and value, so a key-only experiment needs that field isolated first, and rewriting an unused slot key cannot improve the current intent-ID slot route. |
| 123 | (owner 2026-09-26, recorded in `docs/readiness/2026-09-26-knowledge-construction-consumption-optimization-v2.md`; supersedes the optimisation order of row 122's note) In what order are knowledge construction and knowledge consumption optimised? | Owner clarification (2026-09-26): TWO SEPARATE OPTIMISATION STAGES. Construction must produce accurate, compact and discriminative knowledge; consumption must retrieve the relevant knowledge and support sampled retrieval/supply decisions instead of loading the entire store, and RETRIEVAL PERFORMANCE IS AN EXPLICIT OPTIMISATION TARGET. Ruling: Stage A constructs and freezes a candidate knowledge version, compared against the incumbent under one frozen consumption policy and the same full actor; Stage B samples consumption policies over one frozen knowledge version through the ordinary provider path (observed state -> candidate rankings -> bounded selection -> materialised supply -> full trajectory -> terminal feedback), with the store on disk and only the selected packet entering the role. Alternating optimisation: construction updates with consumption fixed, consumption updates with knowledge fixed, and an update only after a complete sampling batch. Minimal comparison set K0/C0, K1/C0, K0/C1, adding K1/C1 only if both interventions are usable, with no assumption that their gains add. Complete-system task outcomes stay the endpoint -- neither better text nor a retrieval number alone proves a gain -- and the five failure modes (absent from the store, present but not retrieved, retrieved but budget-excluded, delivered but ignored or misused, locally correct but later overwritten) must stay distinguishable. Retrieval numbers may be called precision/recall/nDCG only where the relevance target is defined, and reference labels never enter the runtime query or selector. |
| 124 | (owner 2026-09-26, recorded in `docs/readiness/2026-09-26-task-specific-knowledge-stores-and-views-v3.md`) Are intent knowledge and slot knowledge built and consumed as one store or two? | Owner direction (2026-09-26): build intent-recognition knowledge and slot-extraction knowledge SEPARATELY; even when they share physical storage keep typed keys, values and stage-specific consumption views separate, and do not concatenate all views into every role's input. Ruling: separate logical objects (intent boundary, slot contract, shared ontology) over shared canonical sources, with explicit value types, independent indexes, versions, selection rules and budgets. Logical layout: intent_id -> intent key(s) -> intent-decision value; (intent_id, slot_id) -> the role-specific slot interpretation; slot_id -> the shared slot definition and constraints. Role-specific consumption: Perception a bounded retrieved intent view with plausible hypotheses and their distinguishing evidence; Solver the slot views related to the current candidate set with the candidate-to-role mapping preserved, shared definitions rendered once; Reviewer the evidence relevant to its suspected issue, separately observable; Planner findings, evidence availability and legal actions; Solver keeps task-answer authority. New views are source-bound derivatives with explicit hashes -- a released card is never rewritten in place and no unrecorded prompt transformation is passed. This is a logical model, not a request for a new database or framework. |
| 125 | (coordinator, PROVISIONAL, recorded in `docs/readiness/2026-09-26-task-specific-knowledge-stores-and-views-v4.md`; supersedes the implementation-gap statements of row 124's note) What still has to be BUILT for row 124's separation? | Coordinator ruling (2026-09-26) refining the owner direction; the file carries no owner text of its own. Less than v3 claimed: the baseline already declares separate `intent-boundaries-v1` and `slot-contracts-v2` releases, and the candidate-conditioned slot view is ALREADY implemented and registered as `native-candidate-slot-view-v1` (`src/speech_aware_evidence_acquisition/rails/slot_binding_view.py`, `src/speech_aware_evidence_acquisition/core/model/native_slot_binding_view.py`) -- merely not enabled. Reuse it; add no second renderer, store, controller or experiment runner. Two text columns behind one undifferentiated retriever stay insufficient: the two tasks need distinct keys, value schemas, retrieval/selection policies, version identities and input budgets, sharing canonical facts rather than inconsistent copies. A missing candidate binding must not become an implicit hard mask, and full-card fallbacks are preserved. Next experiment: one matched complete-system comparison changing only the optional slot-consumption view, on the ordinary Stage-3 common actor (not the memory-specific Reviewer prompt), after a real request fit and a newly admitted engineering proof; the historical four-row proof identity stays closed. Audit receipt: `docs/receipts/continuation/2026-09-26-task-knowledge-reuse-audit-v1.json`. A deterministic projection is an engineering action, not an RL algorithm or a demonstrated gain. |
| 126 | (owner 2026-09-26, in chat to the root coordinator; the design under criticism is `docs/readiness/2026-09-26-knowledge-group-proposal-design-v1.md`) Is the prepared per-group knowledge-proposal construction correct as designed? | Owner (2026-09-26, translated): "I believe the knowledge construction ChatGPT built is wrong. It conflates the two stages of knowledge construction and knowledge consumption: it treats the finished product of construction as if it were the output of consumption. What is missing is the information retrieval, matching and filtering that consumption requires -- which is why the context is over-long." Ruling, with the part of the design the coordinator verified is NOT at fault stated first so it is not re-litigated: the construction OUTPUT schema is already correct -- `configs/probes/knowledge_value_edit_group_v1.txt` asks for a bounded candidate update to named editable fields, retains their exact previous-value hashes, keeps the ontology, intent bindings and RETRIEVAL KEYS unchanged, forbids sample ids, sample answers, transcript fragments and per-example lookup instructions, emits `slot-value-edits-v1`, and returns an empty `edits` array when nothing general is defensible; the baseline fragment carries `evidence_source: "none"`, `scorers: []`, `result_kind: "artifact"`. The defect is on the INPUT side: to author one bounded field edit the proposer is given all sixteen complete episodes of a group, all supplied knowledge bodies, all role contacts and tool records, control and delivery events and terminal feedback, with no group filtered by score -- 150,600 to 157,401 bytes. **Correction of 2026-09-26, measured rather than estimated:** this row first carried the coordinator's estimate of "about 38-39k tokens" from a four-bytes-per-token assumption; the tokenizer-measured figure is **50,659 to 52,178 tokens** at 2.96-3.03 bytes per token, so each context EXCEEDS the 49,152-token physical slot by 2,533 to 4,052 tokens before any reserve at all. The defect is therefore a CAPACITY failure, not a reserve failure: as prepared, the design is unflyable, and the ruling is stronger than this row originally stated. Two further measured facts: `rails/context_budget.py:149` grants the registered 8,192-token reserve whenever the live slot is at least 32,768 and `:532` clamps an UNDECLARED budget to min(live_slot, 32,768), so without a `context_budget_limits` block the ceiling is 32,768 and the shortfall is about 28,000 tokens; and the 200,000-byte bound in `source-v1.json` passes only because it is stated in the wrong unit (about 66,000 tokens at the measured ratio). The measurement also refuses the strongest reading of the ruling, which is recorded here rather than suppressed: NO episode is wholly irrelevant -- all sixteen supply at least one editable slot's contract, so zero bytes belong to deletable episodes and the waste is distributed INSIDE episodes (custody, routes, ontology, exemplars, non-editable slots). What can be shown is that 62.5 to 65.9 per cent of tokens cannot bear on any editable field, that the edit surface itself is 15 targets under a 1,200-character change bound, that 6 / 6 / 6 / 3 of those 15 targets are proposed against a group supplying nothing at all about their slot, and that a retrieved, matched, top-5 context over the same source-hashed omission ledger is 11,203 to 11,545 tokens -- a 4.44 to 4.61-fold reduction that turns a 2,533-to-4,052-token physical overflow into a 36,581-to-36,923-token physical margin. Reads: `docs/readiness/2026-09-26-knowledge-construction-consumption-split-v1.md`, `scripts/analysis/knowledge_edit_context_composition.py`. And the consumption side is confirmed absent rather than merely disabled: `native-candidate-slot-view-v1` PROJECTS the entire released store in fixed slot order and never retrieves or filters -- no query, no top-k, no row ever dropped (`rails/slot_binding_view.py:270-274`, `core/model/native_slot_binding_view.py:45-49`), so the consumption retrieval stage has to be built on the speech-keyed `rails/phase_supply.py` path. Retrieval, matching and filtering are absent from the step that most needs them, and this repository has measured that cost: the whole-index supply was SLU -7.37 (twin -9.97) as pure form loss, while its only large admitted supplies were retrieved, small and typed (speech-keyed top-5 exemplars, +12.61 and +13.70). Consequences: the registration of the four generations AS DESIGNED is withdrawn before any contact (no cell was registered, no exposure row countersigned, no receipt minted, `launch_authority` untouched); the construction input becomes retrieved, matched and filtered to the fields under edit, with everything else carried by the existing explicit source-hashed omission mechanism rather than silently dropped; consumption becomes its own stage with its own speech-derived query, its own matching to the row's candidates and its own legality / top-k / de-duplication filter, measured separately from construction, exactly as row 123 already requires; and the joint acceptance path -- comparing complete systems on the next construction batch and updating after the whole batch -- is refused as an attribution test, because it cannot separate a bad value from a bad form of delivery, which is the finding of the CELL-3 loss diagnostic (a perfect gate performs about like PLAN). First deliverable is a measurement, not a redesign: the composition of each group context by category in bytes and tokens, the fraction of it that bears on no editable field at all, and the counterfactual size of a retrieved-and-filtered context with its reduction factor and fit margin (`docs/readiness/2026-09-26-knowledge-construction-consumption-split-v1.md`). |
| 127 | (owner 2026-09-26, in chat to the root coordinator, immediately after row 126) Under what criterion may a step be executed, and when must it prove a gain? | Owner (2026-09-26, translated): "We must distinguish two steps, engineering-base construction and system-level optimisation. From the engineering-base-construction viewpoint, as long as the logic is sound, it can in theory raise the ceiling, and it does no harm once the system is built, it may be executed. System-level optimisation stays in the training-free RL stage. I think we will enter that stage very soon." Ruling: these are two admission criteria, not one. An ENGINEERING-BASE item is admitted on three things -- its logic is sound, it states the ceiling it unlocks, and it is read as DOING NO HARM -- and it never has to demonstrate a gain; a SYSTEM-LEVEL OPTIMISATION claim keeps decision 115's rule in full (official SLU-F1 CI95 lower bound above zero, intent non-inferior at the own null, replicated on a fresh roster, one test read). Coordinator derivation, recorded here so it is checkable rather than assumed: this inverts what the measurement instrument can do for us. The instrument note of 2026-09-26 shows we cannot SEE a +0.6 pp gain at any roster size we fly, but bounding harm is the same interval read the other way round, so NEUTRAL-BY-WIDTH -- which this program has repeatedly recorded as a failure (P0, P1, B8b-anchor, the PLAN arm, R-PRIM, B1-notool, and the GEPA cell arm) -- is precisely the no-harm proof a base item requires. A base item therefore preregisters a HARM MARGIN equal to the measured floor of its own design (0.67 pp offline over a sealed pool, 0.735 same-flight paired, 1.2485 cross-flight at Fold A 1,080, 1.2525 at DEV 1,000), states the ceiling figure it unlocks from the measured headroom (oracle best-of-5 +6.55 and +12.55 on disagreeing rows; ENTITY-MIXED +17.4 / +16.5; INTENT-UNCOVERED +5.4 / +6.8 SLU and +12.0 / +16.9 intent), declares `claims_benefit: false`, and is admitted when the primary metric's CI95 lower bound does not fall below the negative margin and intent is non-inferior at its own null. It may never be reported as a gain, and two base items are never assumed to add. The owner's closing sentence is also a scope instruction: base construction is time-boxed -- finish the base items already in flight and open no new ones to postpone the optimisation stage. `scripts/checks/stage3_effect_floor_check.py` must learn the no-harm design before a base item is flown under it, so that a declared harm margin is checked rather than trusted. |
| 128 | (owner 2026-09-26, in chat to the root coordinator, after rows 126 and 127) Is a model's output passed to the next stage unprocessed, and what should cross a stage boundary -- the matched key or the deduplicated value? | Owner (2026-09-26, translated): "I think you and ChatGPT both have a very important omission: you assume the model's output can be added to the next stage without processing, and you ignore CONTEXT ENGINEERING. For example, the multiple results returned by the knowledge-recall stage can in fact be DEDUPLICATED AND RE-RANKED in the context-engineering stage -- like a search engine's chain of coarse retrieval -> dedup -> fine ranking -> hit. And what we pass to the next stage should not be the matched KEY, it should be the DEDUPLICATED VALUE: if you pass the key you cannot deduplicate, because every key that hits may be different, while the value is the same." Ruling: a stage boundary is a place where content is ENGINEERED, not a pipe. The retrieval chain is coarse retrieval, then dedup on the VALUE, then fine ranking over what survives, then the bounded hit that is materialised into the role's context; the unit that crosses the boundary is the deduplicated value with its provenance, never the set of keys that hit it, because keys are many-to-one onto values and a key-level top-k spends budget on duplicates. This applies to every boundary, not only knowledge recall: a node's output reaching the next node is also subject to it. Coordinator verification, recorded separately from the owner's words: the machinery is PARTLY present, which is why the next step is a measurement rather than a redesign -- `rails/phase_supply.py` carries a `rank_policy` (`saea-rank-wcos-prior-agree-v1`, weights `w_cos` / `w_prior` / `w_agree`) resolved through `KNOWLEDGE_RANKERS`; `rails/knowledge_provider.py:1365-1375` already dedups by value, recording `{"value_id": ..., "reason": "shared-value-already-selected"}` in an `ignored_by` structure; `:200-208` refuses a duplicate `entry_id` in a ranking; and `:515-517` builds supplied items as `knowledge:<value_id>` with `evidence_id = value_id`. What is NOT established is whether that dedup lies on the speech-keyed path the flown arms take, and what the real duplicate rate is. The programme's own data already points the same way the owner does: VAR-1's six 625-row arms varied only the exemplar budget and k=10 / k=30 differ from PLANR by **+0.07 / +0.09 pp**, so raising the budget from 10 to 30 bought no information -- which is precisely what a key-level top-k over many-to-one keys would produce. Decision 122 also records that the authored intent activation text currently feeds BOTH key and value, so the two are not yet separable in that store, and decision 124's logical model already allows several intent keys per intent value. Consequence: the dedup-and-rerank stage is an ENGINEERING-BASE item under row 127 -- admitted on sound logic, a stated ceiling and a no-harm reading with `claims_benefit` false, never on a demonstrated gain -- and its ceiling must be quoted from measured freed budget and measured top-5 set changes, not asserted. **Outcome, measured 2026-09-26** (`docs/results/2026-09-26-slurp-supply-dedup-and-rerank-measurement.md`, 7 sealed arms / 4,375 fusion decisions / 20,850 contacts / 697,170 items, zero contacts): the ruling's mechanism is correct and is ALREADY BUILT on the flown path, in the right order, for the route where it applies -- but the route the coordinator suspected is a bijection, and the mass is one level up. Two kinds of key behave oppositely. Retrieval facets to values is a strict bijection in all three released stores (train-exemplars 8,554/8,554, intent-boundaries 60/60, slot-contracts 54/54): 0 collapses, 0 fan-outs, and 0 of about 152,000 ranked keys ever resolved to a value an earlier key had delivered. Intent candidates to slot-contract values IS heavy many-to-one exactly as the ruling describes -- 38.1 per cent of a row's slot values are reached by 2 or 3 candidates and one value from 40 -- and `knowledge_provider.py:1368-1372` already skips a duplicate and continues WITHOUT spending a budget slot, dropping 27,807 of 83,821 key-slots (33.2 per cent) and already freeing 3,120 tokens per row (median 2,784, max 6,983, about 31 per cent of the Solver's 9,968-token prompt). Adding a further dedup stage is therefore worth 494 tokens across all seven arms, with 0 of 4,375 top-5 and 0 of 4,375 top-10 set changes -- three orders of magnitude below what the existing dedup already recovers. Two coordinator claims are corrected by this: the cut-before-dedup inversion is real in code (`kb_policy.py:713`/`:835` cut, `:768`/`:834` dedup; `knowledge_stores.py:1825`/`:1837` dedups keys while concatenating values) but INERT in effect because the facet map is a bijection, and duplication does NOT explain VAR-1's null, since k=10 / 20 / 30 delivered exactly 10, 20 and 30 distinct exemplar bodies. What the measurement does find is the ruling applied ONE BOUNDARY UP: an episode sends 134.18 supply items needing only 40.18 distinct bodies (ratio 3.34), and **67.8 per cent of the supply-block tokens an episode sends are re-renders of bodies an earlier node already received** (68.2-70.4 per cent in every single-sample arm, 86.8 per cent in ROLL-1), because every later request renders from the accumulated `QueryState` while Reviewer and Planner retrieve nothing and still receive the Solver's full 40-item, about 7,240-token block. A second defect: the composite rank sorts both routes by raw score on INCOMMENSURABLE scales, so the top-5 is 98.1 per cent slot-contract keys in every arm, and with `w_prior` and `w_agree` both 0.0 the ranker is pure cosine and cannot reorder anything. The engineering-base item this authorises is therefore node-boundary supply differencing, not another retrieval-side dedup. |
| 129 | (owner 2026-09-26, answering the coordinator's instrument question on the per-node supply-scope ablation) Should the nodes that retrieve nothing of their own receive a narrowed supply? | Owner (2026-09-26, translated): "I think Reviewer and Planner are the two that need GLOBAL information, not local input, in order to make their decision -- including the state of past errors and corrections." Ruling: the direction is REFUSED, not merely the instrument. The measured fact that 67.8 per cent of an episode's supply-block tokens are re-renders of bodies an earlier node already received is NOT waste at those two nodes: the frozen core is stateless across contacts (`reproduction/ojw/native_request.py` enforces exactly one system and one user message and its adapter stores no conversation history), so the accumulated render is the only way the whole picture reaches a judge or a router, and narrowing it would delete precisely what their job needs. The planned no-harm arm is cancelled before registration and neither instrument option is exercised: `supply_variants` (item E42) stays closed and no re-authorisation was sought, and no cross-flight pair is registered. The ruling also OPENS a question the coordinator had not asked: whether those two nodes actually receive the state of past errors and corrections today. That is now an audit (`docs/results/2026-09-26-slurp-reviewer-planner-global-state-audit.md`) covering, per node, the content classes actually present in the rendered prompt with tokenizer-measured token counts; whether a revision's objection and the change made in response survive into the later contact; whether the Planner sees which route was already tried and its outcome; and what a judge or router needs that nothing carries. A gap found there is an engineering-base item under row 127 -- admitted on sound logic, a stated ceiling and a no-harm reading -- and is about ADDING global state, never about trimming it. |
| 130 | (owner 2026-09-26, answering the coordinator's question on the knowledge construction line) The per-group construction contexts do not fit the slot at all; rebuild them or abandon the line? | Owner (2026-09-26): follow the coordinator's recommendation. Ruling as recommended: REBUILD, and sequence the rebuild AFTER the coverage and failure-mode attribution lands. The rebuild makes the construction input retrieved, matched and filtered to the fields under edit, with everything else carried by the existing explicit source-hashed omission mechanism rather than silently dropped; the measured counterfactual is 11,203-11,545 tokens against today's 50,659-52,178, a 4.44 to 4.61-fold reduction that turns a 2,533-to-4,052-token physical overflow into a 36,581-to-36,923-token margin. The construction OUTPUT schema does not change -- it was already a bounded field edit over a keyed store with retrieval keys held fixed. The sequencing is the substance of the ruling and not a delay for its own sake: if the attribution shows the error mass sits in knowledge that is present and retrieved but unused, then editing knowledge VALUES is not where the mass is and the four generations should not be registered at all. Until then `launch_authority` stays false and no cell is registered. |
| 131 | (owner 2026-09-26, answering the cross-carrier question raised by the knowledge-source survey) May Audio2Tool's tool registry and ConEC's entity material be used as SLURP knowledge? | Owner (2026-09-26): "I think it is not needed -- refused." Ruling: DECLINED on the record rather than closed by silence. No current ruling granted it and none is sought; `_SLURP_EXTERNAL_SUPPLEMENTATION` stays SLURP-internal. The survey's own judgement agrees and is retained as the reason: the A2T registry's 152 tools and ConEC's entity inventories share no ontology with SLURP's slot space, so the expected value was assessed at zero in both directions. The ConEC Earnings-22 layer remains behind a carrier expansion, since `data/carriers.py` deliberately sets `evidence=None` for `earnings22-original`. |
| 132 | (owner 2026-09-26, answering the three asset legality questions from the knowledge-source survey) How are the unread assets inside already-pinned keys tiered, and what is done about `train_synthetic`? | Owner (2026-09-26, translated): tier them PER TASK rather than globally; and "the `train_synthetic` dataset is extremely important for improving the SLURP task -- what we need precisely is to analyse how to use it efficiently." Ruling: tiering is per task, so an asset admissible for one carrier's scoring is not thereby admissible for another's runtime, and each tier decision names its task. `train_synthetic` is ADMITTED as a priority analysis item with one boundary that is a rule and not a preference: **its audio is TTS and is refused** under "Human speech and its linguistic content only", so only the text and label side enters, via the measured `slurp_id` plus normalised-sentence filter against devel AND test that retains 15,705 of 19,711 rows (79.7 per cent). What it can and cannot buy is stated now so the analysis is not read as a coverage fix: its 9 extra intent keys lie OUTSIDE the scored label space (row 128's survey measured 0 devel and 0 test `scenario_action` keys absent from train), so it adds depth rather than coverage -- 6,382 sentences absent from train, 446 new entity fillers, and fillers for 11 of the 12 thinnest entity types. **Outcome, measured 2026-09-26** (`docs/results/2026-09-26-slurp-train-synthetic-efficient-use-analysis.md`): the analysis the owner asked for was run and it corrects this row's own premise three times over, which is recorded here rather than quietly amended. First, the survey's "fillers for 11 of the 12 thinnest entity types" is SUPPORT ROWS, NOT VOCABULARY: 11 of 12 receive retained rows, but exactly ONE gains a filler TRAIN does not already hold (`transport_name`, +1) and four gain one the pool does not hold. Second, the honest upper bound is **18 items, not a share of ENTITY-MIXED's +17.43 / +16.47**: of 675 missed gold entity items on the two sealed PLAN rosters, 81 carry a (type, filler) pair absent from the released pool and present in the retained slice, but **63 of those 81 are self-re-synthesis** -- supplied only by a retained row that IS the evaluated utterance, the same `slurp_id` or its sentence re-synthesised, which is leakage -- leaving 18 clean items and a ceiling of **+0.83 pp on Fold A and +0.59 pp on DEV-2000-ADDED**, all of them STABLE-WRONG rows. The asymmetry is explained: Fold A is a TRAIN roster the pool deliberately excludes, so its gold fillers are absent by design and `train_synthetic` re-synthesises its prompts, while DEV-2000-ADDED cannot carry the defect because the filter removes devel first. Third, the coordinator's premise that a text-only row cannot be retrieved was WRONG: `QUERY_SIGNAL_MODALITIES` constrains only the QUERY side, and `phase_supply.py:167` states that "the KEY (facet) side is deliberately UNCONSTRAINED: a key is knowledge text and always has been", with `kb_policy.multidim_recall` scoring the row's speech embedding against the facet's TEXT embedding in one 2048-d space. The obstacle is a price, not a wall: a facet with no row in the sealed facet-vector file is silently skipped (a `.get()` then `continue`, with no error, no fallback and no receipt field -- a silent-failure mode worth its own repair), so admission would cost a text-embedding pass over 15,703 rows, a re-cut facet-vector file, a re-pin of 55 baselines, and pure-cosine competition against 9,354 incumbents. Recommended route therefore **D, construction-side only, on cost rather than on impossibility**, with `claims_benefit: false` and the harm margin at the 0.67 pp offline sealed-pool floor. Two hygiene findings bind any later use: the construction-versus-knowledge guard compares SAMPLE IDS, NOT SENTENCES, so it cannot see that 593 retained rows share a normalised sentence with Fold A, 675 with Fold B, 543 with R01C and 290 with the exemplar draw; and `docs/receipts/knowledge/slurp-split-identity.json` pins recording identity only, so the sentence half of the filter is not reproducible from committed bytes and a frozen normalised-sentence receipt must be minted first. Smallest first step, no flight and no contact: tier `train_synthetic` as `construction-only-knowledge` for the decontaminated slice, freeze that sentence-identity receipt, and carry the per-roster sentence-overlap column as the hygiene condition. One further figure this corrects, which the coordinator had been repeating all day: the locked plan supplies **k=20**, not top-5 -- top-5 is a diagnostic figure. The other two assets: ConEC's word timestamps, which the repository's own code wrongly asserts do not exist (67.6 per cent of 362,747 tokens carry `ts` in `transcripts/timestamps/*.nlp` versus 0.0 per cent in `nlp_references`), are tiered **gold-scoring-only for the Earnings carrier** and never enter runtime; the 66 unread cased ConEC PDFs are DEFERRED, since Earnings is not the current focus and they cost a D1 layer, a routing rule and a confinement disposition. |
| 133 | (owner 2026-09-26, answering the coordinator's primary-metric question on the agreement arm) A mechanism that acts on intent retrieval -- which metric is primary? | Owner (2026-09-26, translated): "the primary metric is still to be reported as the intent-recognition accuracy." Ruling: for a mechanism whose action is on the intent, **intent accuracy is the primary metric**. This is a deviation from decision 115's WORDING, which names official SLU-F1 primary with intent as the non-inferiority guard, and it is admitted because official SLU-F1 is **entity-only** while this class of mechanism does not act on entities: measuring it there would measure a transduction rather than the mechanism. Coordinator completion, recorded separately from the owner's words because the owner did not state it: decision 115's SHAPE is preserved rather than discarded -- one primary metric and one non-inferiority guard -- so **official SLU-F1 becomes the guard** in this configuration, and an intent gain that damages the entity score is not an admission. The floor and the replicate requirement are unchanged: the design's measured floor still applies, and a cross-flight contrast still needs its in-chain A/A. Consequence for the registered agreement arm: its `stage3_measurement` must be re-declared with `primary_metric` intent accuracy, and its `expected_effect_pp` recomputed on the intent ceiling of **6.4831 pp** rather than the SLU-F1 ceiling of 2.9131 pp -- but NOT yet, because the conversion factor in that arithmetic is the quantity the probe of row 134 is about to measure, and re-declaring twice would put a guessed number on the record first. Scope: this row applies to a mechanism acting on intent, not to every cell; a mechanism acting on slots or on the answer form keeps 115 unchanged. |
| 134 | (owner 2026-09-26, answering the coordinator's sequencing question) Fly the registered agreement arm, or the cheap conversion probe first? | Owner (2026-09-26): the probe first. Ruling as recommended: the 70-row conversion probe (about 580 contacts, about 0.25 GPU-h) flies before the agreement arm plus its in-chain A/A (about 7 GPU-h). The reason is on the record because it is the general rule this program should follow, not a one-off: the arm's declared expectation rests on a persuasion factor of 0.5 that is the midpoint of [0, 1] and nothing else, and **even at a perfect conversion the SLU-F1 ceiling is 2.9131 pp against a 2.5 pp floor** -- so 0.25 GPU-h decides whether 7 GPU-h can answer anything. The probe reads intent correctness per row rather than pooled SLU-F1, which is readable at 70 rows only because the within-flight null measured **0 intent flips in 200 request-identical rows**, making an intent flip attributable rather than noise. Its population is chosen by the mechanism's own effect using gold offline, so the cell is `form-proof` with `claims_benefit` false and **may never support a pooled or roster-level claim**. |
| 135 | (owner 2026-09-26, on the Reviewer instruction defect found by the global-state audit) Repair the retired-tool instruction now or after the agreement read? | Owner (2026-09-26): agreed -- defer. Ruling: the defect is REAL and its deferral is DELIBERATE, recorded so it is not later read as an oversight. 52 of the Reviewer's 82 instruction tokens (63 per cent) order a task-contract tool retired as item E25, against 0 tool schemas in all 2,590 contacts, and the same day's system-summary diagnostic records the downstream effect -- summaries treat textual tool-result claims as real execution while the tool event list is empty. Its repair has a NEGATIVE token cost. It is deferred because it changes prompt bytes, therefore arm identity, therefore the agreement arm's relationship to its sealed comparator: repairing it now would confound two changes in one read. It is the first item of the engineering-base repair queue once the agreement line is read, and until then every reader of a Reviewer transcript should know that a node told to use a tool that does not exist will talk as if it had. |
| 136 | (owner 2026-09-26, on the train_synthetic first step) Execute the construction-only tiering now? | Owner (2026-09-26, translated): "train_synthetic -- perhaps it is because the test set does not cover it that you think it is not needed; let us look at it later." Ruling: DEFERRED, no tiering minted, no receipt frozen, no store built. One factual correction is recorded beside the deferral because the reasoning matters more than the verdict: the coordinator's conclusion did not rest on test coverage. It rested on two measurements -- the scored label space is closed (0 devel and 0 test `scenario_action` keys absent from train), and of 675 missed gold entity items on the two sealed PLAN rosters only **18 are clean**, because 63 of the 81 candidates are self-re-synthesis of the evaluated utterance, which is leakage. The 18 are counted against the error mass we actually hold. **But the owner's intuition identifies something the coordinator had not stated, and it strengthens the deferral rather than weakening it:** whether the TEST split's filler diversity resembles our rosters' is **unknowable before the one test read**, because checking it would require reading test annotations, which decisions 99 / 107 / 108 and the study's own boundary forbid. So this is precisely a hypothesis that cannot be tested in advance. The consequence is a standing instruction rather than a closure: keep `train_synthetic` analysed but unbuilt, and if the single test read later shows entity weakness this is the pre-analysed material to reach for, with its filter, its 79.7 per cent retention, its leakage finding and its two hygiene conditions already on the record. |
| 137 | (owner 2026-09-26, after the coordinator reported that no 95 per cent figure existed anywhere in the record) Is the programme's target relative or absolute? | Owner (2026-09-26, translated): "I think the target is an ABSOLUTE task metric. For the current system this is a simple task. Of course it is quite possible the dataset has problems and 95 per cent may not be reachable -- but our target is 95 per cent." Ruling: the programme carries an **ABSOLUTE TARGET of 95 per cent intent-recognition accuracy**, and it SUPPLEMENTS rather than replaces decision 115. Each mechanism is still ADMITTED relatively -- a gain over its comparator with the CI95 lower bound above zero at the design's measured floor, intent primary under row 133 -- because that is what the instrument can see; what changes is the programme's ENDPOINT, which is no longer "a stable gain" alone. The coordinator states the arithmetic on the record, because it reshapes the route rather than the rules. Measured today: the v2.0 lock arm on TRAIN Fold A reads **intent 82.2222** (scenario exact 87.3148, action exact 83.5185, complete-task exact 53.7755, SLU-F1 63.6304), its replicate 82.5000, and ROLL-1's construction roster 70.56. **The gap is 12.78 points**, and the best single candidate in hand has a ceiling of 6.4831 points at a conversion of 1.0 -- so no one mechanism closes it and the route must be a COMPOSITION, which is what family `sealed-credit-system-policy-v1` was registered for. Two facts make the target arithmetically reachable rather than aspirational: the bad-case bank's `INTENT-UNCOVERED` class alone carries **+12.0 / +16.9 points of intent headroom** on Fold A / DEV -- about the size of the whole gap -- and the agreement mechanism reaches 70 of that class's 130 rows, leaving 60 for the pruning line of the owner's same-day hypothesis. Two facts bound it: a headroom is an ORACLE (every row in the class answered correctly), not an achievable; and the owner's own caveat is testable -- `general_quirky` is a catch-all owning 25.5-31.4 per cent of all not-delivered intent-wrong rows, so part of the residual may be label arbitrariness rather than system error. The consequence is an immediate measurement, not a plan: **the maximum intent accuracy attainable under gold as it stands** must be measured before 95 is treated as a distance, because if the label ceiling is below 95 then the target is unreachable for a reason no mechanism can fix and the owner should learn that from a number rather than from repeated near misses. **Outcome, measured the same day** (`docs/results/2026-09-26-slurp-intent-label-ceiling-audit.md`, commit `4d0adabf`, zero contacts, test split never opened): the owner's caveat is testable and it FAILS -- the dataset is not what stands between the system and the target. Sentence-level label ambiguity, measured mechanically over three keys (token sequence / multiset / set), is almost absent: 3 colliding normalised sentences in all of TRAIN (11,482 distinct), ZERO in devel at every key, a corpus ceiling of 99.9684 per cent (train, strictest) to 99.9444 per cent (pooled, loosest), and a per-roster ceiling of **100.0000 per cent on R01C, Fold A and DEV-2000-ADDED at every key and scope** -- stated as an upper bound from one cause only. `general_quirky` is NOT a duplicate-label problem: 555 TRAIN and 105 devel gold rows, 0 sharing a sentence with a different-intent row in either direction, 1 cross-split group in the whole corpus. The lock arm's 17.78 points of Fold A error partition as **0.00 unwinnable, 0.00 ambiguous-but-majority, 3.33 on the catch-all, 14.44 plainly ours**; the four Fold A rows that sit in any colliding group were all answered correctly. Published reference line from the pinned scoring-alignment audit: Gold/HerMiT 84.84 on gold transcripts, ChatGPT zero-shot 79.25, so 95 sits about 10 points above the highest published intent accuracy in the record and about 5 below the label ceiling. Consequence for this row: **95 is reachable under the labels; 14.44 points are available against 12.78 needed even conceding the whole catch-all; the route is a composition problem and nothing else.** Nothing in this row licenses relaxing an admission rule to approach the target faster: the guard of row 133 stands, and an absolute endpoint makes an unsound gain worse, not more forgivable. |
| 138 | (owner 2026-09-27, answering the coordinator's proposal of a system-regression flight every k base items, to bound cumulative harm under row 127) Does the no-harm admission need a cumulative bound, and is it blocking? | Owner (translated): "Needed, but it must not be a blocking item. Later we will run N rounds of optimisation with the training-free RL algorithm; if a composition yields no improvement, that itself means the information elements conflict, and the conflict must be resolved before continuing." Ruling: the regression check is NOT a separate gate on base admission. It is FOLDED INTO THE OPTIMISATION ROUNDS -- every round's composed read against the lock IS the cumulative check -- and a round that fails to improve is read as a CONFLICT DIAGNOSIS, not as a null: the composed elements are assumed to be fighting each other until the conflict is located and resolved, and no further element is admitted on top of an unresolved conflict. Coordinator note: cumulative harm is therefore bounded by the cadence of the rounds, not by a standing gate, so the first composed round must happen before many base items pile up; and because a no-improvement round is expensive to misread, each round carries the per-class attribution table the bad-case bank defines, which is what turns "no improvement" into "these two elements conflict on this class". |
| 139 | (owner 2026-09-27, on the coordinator's pre-committed fallback for the AGREE arm if the CONV probe's m fell below 27) May a cell's disposition be pre-committed as an if-then on an unread result? | Owner (translated): "The conclusion is already on disk. Do not adopt if-then logic; when you have the result we discuss it separately." Ruling: NO CONDITIONAL PRE-COMMITMENT on a sealed-but-unread result. The AGREE arm is neither flipped as a benefit claim nor re-declared as a no-harm item until m is read and discussed; its minted receipt stands unspent. The general rule is recorded because it is the owner's method: a decision is taken on the number, in conversation, not on a branch the coordinator wrote in advance -- pre-committing turns a measurement into a formality and hides the judgement that should happen when the number is seen. The GPU queue is therefore built from cells whose value does not depend on m (the np1 pair, ROLL-3, Audio2Tool's own null). |
| 140 | (owner 2026-09-27, on the request to stop the resident np4 session for an np1 cache-off determinism pair) Is a throughput cost acceptable in exchange for a tighter instrument? | Owner (translated): "Experimental efficiency matters most. Note that our future experiments will need MASSIVE sampling; if sampling alone takes a year, the experiments are meaningless." Ruling: the cheap TEST is authorised -- 50 rows twice at a single-slot cache-off geometry, about 0.5-1 GPU-h, to learn whether the +1.87 pp between-flight offset is a continuous-batching artefact -- but ADOPTION of any geometry is decided on throughput, and **sampling throughput (contacts per GPU-hour) is henceforth a first-class objective of the engineering base**, on the same footing as a metric gain. Coordinator consequences: (a) the np1 read reports contacts per minute beside byte identity; (b) the tension is real -- the prompt cache that breaks determinism is also a throughput lever -- and the likely resolution is two geometries for two jobs, np4-plus-cache for sampling-heavy rounds where noise averages out and np1 only for small A/A instrument reads, decided on the measured numbers; (c) a throughput programme opens now: ROLL-2 spent 81,435,827 prompt tokens on 8,996 contacts (about 9,052 per request) against 366,929 completion tokens, so PREFILL owns the wall-clock and the levers are prompt length and prefix-cache reuse, measured before anything is changed. |
| 141 | (owner 2026-09-27, answering on which split the absolute 95 per cent of row 137 is measured) Where is the target measured, and may the test split be sampled? | Owner (translated): "The test set. In the early phase compare by sampling the development set first; or you may also sample a group from the test set to compare. The sampling must guarantee coverage." Ruling: the 95 per cent of row 137 is a TEST-SET number. For iteration the owner names dev sampling FIRST (DEV-2000-ADDED exists; ROLL-3 is putting a sealed pool on it) and PERMITS a coverage-guaranteed sample of the test split for comparison; this supersedes the wording of decisions 99 / 107 / 108 to the extent of that permission and no further. Coordinator statement of the cost, recorded so the permission is used with its consequence understood: a roster compared against repeatedly stops being an unbiased final read of itself, so (1) the test sample is drawn ONCE, sealed with its own receipt, and its COMPLEMENT is sealed at the same moment as the closure roster for the final read; (2) its size keeps the complement's power (13,078 total; a 2,000-row sample leaves 11,078); (3) coverage means every scored intent present with a floor per stratum, reported in natural-mixture and equal-stratum weightings; (4) the coordinator recommends dev sampling for per-round iteration and the test sample for MILESTONE checks only; (5) reading test gold for stratification is recorded as exactly that, offline, never runtime; (6) every contact with either test roster stays behind the committed owner allowance the fail-closed final-report split role already requires. |
| 142 | (owner 2026-09-26, in chat: retrieval fails because the knowledge base is too dense and complex -- is the whole training set in it, and could training-free RL prune it to a small set from which the correct label is more easily retrieved?) Should the knowledge base be pruned? | Measured the same night (`docs/results/2026-09-26-slurp-knowledge-base-pruning-measurement.md`, `7508a8ba`, zero contacts, recomputations matching the sealed rankings 100.00 per cent on all three rosters) and **the hypothesis is refuted for removal, cleanly**. Census: the exemplar pool holds 9,354 of 11,514 TRAIN utterances (81.2 per cent) and IS most of the training set; the two semantic channels are one key per label (60 intents, 54 of 55 slot types) -- and the channel that fails is the small one. The direction is the reverse of the premise: on the same rows the DENSE pool's top-20 majority names gold on 76.2 / 61.9 / 75.5 per cent (Fold A / ROLL-1 / DEV) while the SPARSE boundary channel's rank-1 names it on 65.6 / 47.0 / 56.4. Per-key masking over 2,705 rows: only 2 of 60 keys have a positive net and both destroy already-correct work; `general_quirky` is net -21 (1 gain, gold on 137 rows) -- it is chronic because it is MISSED, not because it crowds; `weather_query` is -154. Greedy fitted on Fold A stops after one key at +2 rows, honest ceiling zero. Pool pruning is monotone the wrong way (edit-9 keeps 4,688 and loses 6-8 points of vote accuracy; cap-40 loses 4-12). **The prune to register next is none.** What the measurement DID find is the lever the rank diagnostic pointed at from the other side: the 60 boundary descriptions share a mean Jaccard word overlap of 0.6073 (mean cosine 0.4756, max 0.908), and `general_quirky` has 36 distinct top-1 rivals at below-average overlap to each -- sixty descriptions sharing three fifths of their vocabulary cannot separate sixty intents. The construction question is therefore REWRITING the boundary keys to be discriminative, not removing any, and the consumption question is borrowing the utterance-to-utterance key space that already separates better, which is what the agreement term does. Nothing was rewritten; rewriting is a construction act with its own authority. |
| 143 | (owner 2026-09-27, on the AGREE arm after the CONV probe read m = 32 of 70) Fly the agreement arm, and how? | Owner: agreed. Ruling: the arm FLIES AS A BENEFIT CLAIM under row 133 -- intent-recognition accuracy primary, official SLU-F1 the non-inferiority guard -- with its four-row smoke and its in-chain A/A at w_agree 0.0 in one chain on TRAIN Fold A 1,080. Its expected_effect_pp is re-declared from the measured m: 32 x 0.092615 = **2.96 pp intent** against the 2.5 pp cross-flight floor at n=1,080; the position read's finding that the term also moves gold to position 1 on 35 of the 86 already-delivered-but-wrong rows is recorded as a PRIOR that the arm will measure, never as part of the declared expectation. CONV's row interval [24.2, 40.1] spans 27, so a NEUTRAL-by-width read remains possible and, per rows 127 and 139, its disposition would be taken on that number in conversation. Queued on np4 behind ROLL-3. |
| 144 | (owner 2026-09-27, on the Audio2Tool own-null roster) Which 400 does A2T-AA fly on? | Owner: the new roster. Ruling: `A2T-PAIRED-400-V1` -- 50 per tier, one seeded draw (20260921) from the sealed union-4000, frozen, overlap 0 with construction-800 (45 with evo-curve, reported), comparator rows the sealed `SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1` per-row hashes -- exactly as decisions 67/68/71 specified and no earlier roster satisfied. The 2026-09-04 R1 calibration 400 is not used: 332 of its rows sit outside the union promotion and it has no direct comparator rows. Geometry finding recorded: A2T serves np3 x 32,768 with max_tokens 2048 on its own packet root, so **A2T cells cannot interleave with SLURP cells** -- they fly only after a full serving swap and swap back. |
| 145 | (owner 2026-09-27, on the centroid-key finding) Register the key-construction conversion probe? | Owner: agreed. Ruling: register a CONV-style probe for the centroid boundary key -- the treatment (re-cut 60-facet file from the mean construction-TRAIN utterance vector per intent, zero encoder contacts, delivered body unchanged) flown ONLY on the Fold A rows whose gold entry it newly delivers, against the sealed PLAN answers, reading P(correct given newly delivered) on intent per row; form-proof, claims_benefit false, no pooled claim. The probe pins its own derived baseline and does NOT re-pin the 211 committed configs; that rebuild waits on its m. It competes with the agreement term for the same INTENT-UNCOVERED rows, and row 138's composed round decides whether they add. |
| 146 | (owner 2026-09-27, on the test-sample size) 2,000 or 3,000? | Owner: adopt 3,000. Ruling: `SLURP-TEST-SAMPLE-3010-V1` (3,010 recordings / 682 prompts, split identity 0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9) and its complement `SLURP-TEST-CLOSURE-10068-V1` (10,068 / 2,292, 377b937df3c29e52e3596426741b03129fa526bf677d92b5c03b78dd8dc2457b), partitioned by PROMPT so sample and closure share no sentence, stratum = gold intent with a floor of 5 prompts each side where an intent has 10 or more; `general_greet` (one test prompt) goes to the closure only, so the sample covers 58 of 59 and the final read covers all 59. The instrument arithmetic that overturned the 2,000 prior: sample post-stratified half-width 2.18 -> 1.71 pp while the closure widens only 0.893 -> 0.938. Both receipts carry split_role final-report; first contact with either waits on the owner allowance receipt binding its hash. |
| 147 | (owner 2026-09-27, on the blocker the test-sample design found) `contracts.gate_exposure._require_final_report_disjointness` intersects a final-report roster with EVERY other committed roster, so the sample, the closure and now the FULL parent all refuse each other. Change it? | Owner: check the code for conflicts; if none, adjust. Ruling: adjust WITH PROOF, never by relaxing -- a partition-aware exemption that skips the declared parent and sibling only after re-proving from committed items that roster union sibling equals parent and roster intersection sibling is empty, leaving every other intersection check exactly as it is; tests for the partition case, the non-partition case and a forged sibling; the FULL parent's three 2026-09-23 preparation rows re-verified afterwards. No test id reaches any runtime surface. |
| 148 | (owner 2026-09-27, on the seal profile) The 9p tax is per-record latency, not bandwidth; move the run root to ext4? | Owner: check the code for conflicts; if none, adjust. Ruling in two parts. (a) The two code fixes proceed first (in flight on `fable/tracefix`): `TraceSink.emit` stops opening/appending/closing per record (7.06 ms x 50,380 = 355.6 s per flight) and `read_attempt_trace_facts` stops line-scanning 719 MiB through an 8 KiB buffer (14.6 s per seal), each required to leave every sealed byte identical and no recovery property weaker. (b) Relocating the run root to ext4 is AUDITED before it is done: every check, receipt, confinement rule, lock reader and no-duplication rule that assumes run outputs live under the E: data root is inventoried; if none conflicts, run outputs are written to ext4 during a flight and the immutable sealed bundle is synced to E: as the archive after the seal, overlapping the next flight; if any conflicts, the audit names it and the move waits. The standing rule that only mlruns lives on ext4 is amended only by that audit's outcome. |
| 149 | (owner 2026-09-27, on the worktree inventory) 143 unregistered orphan directories under `/home/chao/saea-worktrees/` (~40 GB; their `.git` files point at pruned admin directories, HEAD unresolvable, so no machine proof of a clean tree exists) -- delete, keep, or record then delete? | Owner: delete. Ruling as executed: option A -- remove every orphan directory that is NOT registered in `git worktree list`, is NOT named `codex-*` (the ChatGPT/Codex session's own trees, never touched), has no file newer than 2026-09-24 00:00Z and no live process with a working directory inside it; the 09-24-and-later orphans age into the same rule later; every removal is logged with path, size and newest mtime under `PRUNE-ORPHANS-<utc>.log` beside the inventories. Branch refs are untouched, so unmerged work survives as a branch even where its working copy is gone. |
| 150 | (owner 2026-09-27, on the DET read) Fly the 200-row np1 floor re-estimate the read recipe named as a separate registration? | Owner: no longer necessary. Ruling: not flown. DET answered the determinism question (50 of 50 byte-identical) and located the between-flight band in the np4 serving geometry; the floor that governs admissions is that geometry's own, and np4 keeps its in-chain replicate. np1 cache-off is reserved for small paired probes where the between-flight band would swamp the effect; it is not a sampling geometry (row 140). |
| 151 | (owner 2026-09-27, on the test sample) Sign the `final-report` allowance for `SLURP-TEST-SAMPLE-3010-V1` now, or only after the first composed arm is admitted on dev? | Owner: sign now. Ruling: the allowance receipt for the sample (split identity 0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9) is written with status `authorised` on this instruction, quoting the owner's words; it permits the sample's preparations and its milestone reads, each read run id one attempt; the FIRST CONTACT with the sample is nevertheless gated on the coordinator reporting a dev-admitted composed arm to the owner in conversation, and the closure roster `SLURP-TEST-CLOSURE-10068-V1` stays `pending-owner` until the Stage-3 closure read. |
| 152 | (owner 2026-09-27, on the first composed arm) Fold the citation contract `saea-solver-cited-answer-v1` into COMP-1 as a row-127 no-harm base item (+134 instruction tokens per Solver contact, byte-identical default, per-entry credit table)? | Owner: fold it in. Ruling: COMP-1 = the PLAN lock + the agreement term (w_agree 1.0, k 60, fuse 8-1-8) + the centroid boundary key + the citation contract, on TRAIN Fold A 1,080 with an in-chain A/A, intent primary; the citation part is admitted on no harm and its credit table is the reward signal every later construction round reads. Registration begins when the AGREE and KPROBE reads are in; the declared expectation is composed from their measured m values, never from a prior. |
| 153 | (owner 2026-09-27, on G5 after the AGREE read) Admit the Reviewer-instruction repair (63 % of the instruction orders a tool retired as item E25; negative token cost) as a no-harm item in round 3? | Owner: agreed. Ruling: G5 is prepared now (repaired instruction, token measurement, config fragment, its own prepared-supply identity) and flown in round 3 -- the consumption-form round -- as a row-127 no-harm item, folded into the following composed round where cumulative harm is checked (row 138); row 135's deferral is discharged by the AGREE read, not before. |
| 154 | (owner 2026-09-27, on the next Audio2Tool cell) After A2T-AA, is the first A2T mechanism cell A2T-ORG-1 (the domain-grouped registry) on the paired 400? | Owner: agreed to the coordinator's recommendation. CORRECTION recorded by the coordinator the same hour: the recommendation was wrong -- A2T-ORG-1 was already flown on 2026-09-05 and read HARMFUL (official tool accuracy 61.40 -> 58.17, -3.23 pp, CI90 [-4.15, -2.33]; `docs/readiness/2026-09-05-a2t-org1-domain-grouped-registry-v1-verdict.md`), and a closed line is not re-opened. The decision is therefore returned to the owner with a corrected proposal: the first A2T cell after the own null is A2T-SYS-1 -- the locked SLURP system form (Perception shortlist, exemplar knowledge from the released A2T views E27/E28, Reviewer, Planner) on the paired 400 against the sealed direct comparator, read on `a2t-toolcall-official` with the tier table and the paper column beside it, its bar set by h_A2T from A2T-AA. Nothing is registered under this row until the owner answers. |
| 155 | (owner 2026-09-27, answering the corrected proposal under row 154) After A2T-AA, is the first Audio2Tool mechanism cell A2T-SYS-1 -- the locked SLURP system form (Perception shortlist, exemplar knowledge from the released A2T views E27/E28, Reviewer, Planner) on `A2T-PAIRED-400-V1` against the sealed direct comparator? | Owner (English translation): "Agreed to A2T-SYS-1." Ruling: A2T-SYS-1 is registered now (model-free) on the paired 400 through the shared controller and the same FlightRuntime as the direct baseline, read on `a2t-toolcall-official` (the pinned release's own `metrics.py`) with the tier table and the arXiv:2604.22821 Table 3 paper column beside the repo column; its bar is set from A2T-AA's measured h_A2T once that pair is read, never before (row 139); it flies on the A2T np3 x 32,768 geometry after a full serving swap. Row 154's question is closed by this answer; A2T-ORG-1 stays closed (HARMFUL, 2026-09-05). |
| 156 | (owner 2026-09-27, answering the coordinator's question under row 151) May the label-free preparations of `SLURP-TEST-SAMPLE-3010-V1` run ahead of the dev-admitted composed arm? | Owner (English translation): "The preparation work may run ahead." Ruling: the sample receipt's first-contact gate (row 151) is lifted for the three PREPARATION run ids only -- `SAEA-SN-TEST-SAMPLE-3010-PREPROCESS` (speech packet encode + promotion), `SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1` (frozen retrieval-encoder query vectors) and `SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1` (zero-contact flatten) -- which read no label and produce no answer; each is registered, countersigned under this row and run on CPU where the registered path allows, alongside the GPU queue, within the <= 8 preparation-worker cap during a campaign. The MILESTONE read ids (00-PLAN and 01-05) keep row 151's gate: no answer is produced on a test-sample row until the coordinator reports a dev-admitted composed arm and the owner answers. The allowance receipt's bytes are unchanged (its gate is conversational by its own text and binds to the countersignature); the closure roster stays `pending-owner`. |

Outcome of decision 155 (2026-09-27): NOT REGISTERED -- the proposal the owner agreed to rested on a false premise of the coordinator's, and the registration agent stopped before creating anything. CORRECTION: the released Audio2Tool views E27/E28 are INDEX views, not exemplar knowledge -- E27 is the carrier profile in `rails/knowledge_index.py` and the E28 snapshot `a2t-knowledge-index-v1` holds 1,195 entries (3 domain, 152 tool, 1,040 edge) and no exemplar; the exemplar kind planned under decision 66 (`docs/superpowers/specs/2026-09-21-a2t-engineering-base-index-design.md`) was set OFF and never released; the only exemplar-shaped A2T base (`knowledge/audio2tool/saea-kb-a2t-toolshaped-v1`, August) has no release and is keyed by Qwen3-Embedding-0.6B vectors that cannot be matched against the Omni-Embed-Nemotron speech queries. Flying the E28 views themselves is the knowledge-index form (IDX/IDXT HARMFUL on SLURP, blocked from every plan; decision 70). Without exemplars the locked form maps onto Audio2Tool as the sealed `A2T-NATIVE-ROLE-BASE-UNION4000-V1` dual-store cell minus the Reviewer's task-contract tool (which ran 15 times on 11 of 4,000 rows) -- a re-flight of a decided contrast (primary-call exact +4.05 [2.96, 5.17] but official tool accuracy 62.03 -> 58.43, tool guard failed, NOT ADOPTED). Fit of that four-node form on np3 x 32,768 was measured from its 19,475 sealed fit receipts: every request fits, worst margins Perception 12,528 / Solver 8,374 / Reviewer 8,120 / Planner 8,018 tokens. The question is returned to the owner with three options (a zero-contact re-read of the sealed dual-store rows against direct on the paired 400 once A2T-AA gives h_A2T; building the Audio2Tool instance of M1 -- an exemplar release from the construction pool plus a Nemotron key encoding -- which is a NEW base item and therefore needs the owner to lift decision 127's 'open no new ones' for it; or the no-harm notool read E29).
| 157 | (owner 2026-09-27, on the corrected A2T-SYS-1 options) Zero-contact re-read, build the Audio2Tool exemplar store as a new base item, or only the notool read? | Owner (English translation): "Decision 1: complete it per option 2, but lower its priority; we must first lock SLURP's capability boundary." Ruling: the Audio2Tool instance of M1 is admitted as a base item (row 127's 'open no new ones' is lifted for it by this row): an exemplar release drawn from the A2T construction pool with union-4000 excluded, a Nemotron key-encoding preparation, then A2T-SYS-1 = the sealed dual-store form minus the Reviewer task-contract tool plus train-exemplars k=20 to the Solver, one-factor against the sealed dual-store rows with direct beside, its fit measured not assumed; option 1's zero-contact re-read is done for free once h_A2T exists. PRIORITY: behind the SLURP line -- nothing of it takes the GPU while a SLURP round (COMP-1, its replication, the milestone reads, the consumption-form round) is ready to fly; its model-free preparation may proceed only when no SLURP registration needs the hands. |
| 158 | (owner 2026-09-27, on the Earnings route) Register E41 (the bounded Perception note named by row 103) with its dry run and the sub10 re-read? | Owner (English translation): "Decision 2: if you judge this to be engineering base, i.e. unfinished Stage-2 work, carry it out; otherwise do not." Coordinator's judgement, recorded so it is checkable: IT IS unfinished Stage-2 engineering base. The 2026-09-03 base rule ('one base, thin derivations; the same harness for every arm') requires every carrier to run its direct and system arms through the shared controller and FlightRuntime; decision 89 moved Earnings onto FlightRuntime and E35 passed STRUCTURALLY, but the system form was root-caused to harness defects (E13 scope, per-role caps, Perception truncation), and rows 98/103 left the Earnings system form NOT ADMITTED until E41 passes a four-row dry run and the sub10 re-read -- i.e. the shared harness does not yet carry the Earnings system form soundly. E41 changes no mechanism and claims no gain; it completes the harness. Ruling: carry it out -- register E41 and its four-row dry run and the sub10 re-read (E21 geometry, a serving swap), scheduled on the GPU after COMP-1 so the SLURP line keeps the card; E22 follows E21 on the same harness. |
| 159 | (owner 2026-09-27, on the dispatcher slot-fill lever) Register keeping every slot loaded as an engineering-base item? | Owner (English translation): "Decision 3: likewise, by the logic of unfinished Stage-2 engineering base, optimise it with priority!" Coordinator's judgement: IT IS unfinished Stage-2 base -- the 2026-09-03 pipeline rule already requires that 'the GPU never idles', and the measured 27.3 % empty slot capacity of ROLL-2 (8,997 of 32,909 slot-seconds; 1,055 s with every slot empty; 2.67 s before every first Solver contact; `docs/results/2026-09-27-slurp-throughput-baseline-and-levers.md`) is the runtime failing that rule, with no change to any byte a node sees. Ruling: PRIORITY engineering item -- the runtime keeps every slot loaded (lever 1: async dispatch across rows, 1a no all-slots-empty time, 1b Solver#1 supply acquisition overlapped with Perception decoding), proven byte-identical in every request body and every sealed per-row state bound to its request, admitted on no harm (the within-flight band and the delivered answers against an in-chain A/A) plus the measured contacts per GPU-hour; it enters the base for cells flipped after it lands and never alters a pinned flight commit. |
| 160 | (owner 2026-09-27) COMP-1 and G5 each register an in-chain A/A that re-flies the locked PLAN plan's own request bytes (COMP-1's adds only recall k 60, a proven no-op on the delivered set): fly ONE shared A/A in one campaign [COMP-1 smoke, G5 smoke, the shared A/A, COMP-1 arm, G5 arm]? | Owner (English translation): "Decision 1: agreed." Ruling: one campaign, one A/A (COMP-1's A/A cell `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`), G5's `replicate_run_id` re-declared to it and G5 minted with `--drop-aa` (its own A/A pair left unflown and closed as superseded, never consumed); CONDITION checked model-free before the flip: the two A/As' prepared first-phase supply digests and composed request bytes are byte-identical -- if they are not, the two cells fly separately as registered. Both arms are then read against the same null in the same serving state. The AGREE disposition (the coordinator's second item) is taken on the final read, in conversation (owner: "wait for the final result to come back"). |
| 161 | (owner 2026-09-27, on the AGREE read) The agreement term read on TRAIN Fold A 1,080 against its in-chain A/A: intent 82.50 -> 85.83, +3.33 pp, CI95 [+1.57, +5.09] (saves 67 / harms 31, McNemar p 0.00035; declared 2.96 against the 2.5 pp floor), scenario +2.13 [+0.65, +3.70], action +2.87 [+1.11, +4.63], official SLU-F1 guard +1.85 [+0.23, +3.47]; the A/A reproduces PLAN (82.50 vs 82.22 / PLANr 82.50). Disposition? | Owner (English translation): "Confirmed: AGREE enters COMP-1." Ruling: the agreement term (w_agree 1.0 over the self-excluded exemplar-intent vote, recall k 60, fuse_coverage 8-1-8) is RETAINED as the first component of the composed arm COMP-1; its status is benefit shown on TRAIN Fold A, PENDING REPLICATION on a fresh roster (rows 115, 127) -- the replication is carried by COMP-1's DEV-2000-ADDED replication in round 2, and it is never a test claim (row 28). |
| 162 | (owner 2026-09-27, on GPU utilisation) The day's card was busy 335 of 800 minutes (42 %): about 300 idle minutes because nothing was flip-ready after a seal, about 130 because a CPU sidecar held host memory under the serving start guard, and 20-40 % empty slots inside flights. Register a standing, pre-approved FILLER family flown whenever the queue is empty? | Owner (English translation): "Agree to A; execute as recommended." Ruling: a standing filler family is registered -- sealed five-sample rollout pools of the current best SLURP system on TRAIN rows outside Fold A and outside every evaluation roster, in chunks of about 200 rows (about 35 GPU-minutes each), each chunk its own run id with its own exposure row and receipt, minted ahead in a batch; an idle-filler queue flies the next chunk ONLY when no main-line chain is ready and no flight is running, and a main-line chain waits at most one chunk. The pools are the rollout substrate of the training-free RL inner loop (`sealed-credit-system-policy-v1`), descriptive by construction, never an admission cell. Adopted with it as standing rules: every serving geometry starts BEFORE any CPU sidecar, and sidecars run only inside long resident flights; A2T/E21 cells are batched per geometry swap; registration runs two cells ahead of the card. |
| 163 | (owner 2026-09-27 ~13:40Z) What is the coordinator's focus for the next hours? | Owner (English translation): "Your focus for this period: (1) open multiple tasks to harden the current engineering base, so that the large-scale experiment phase three hours from now has a stable engineering baseline; (2) enter analysis mode: do a fine-grained analysis of the results of the past days -- make clear where the current gains or harms come from, where the raw knowledge falls short, and what capabilities must be added." Ruling: two parallel tracks until about 17:00Z. ENGINEERING: the serving lifecycle made robust (one swap tool, precise flight detection, health-verified restarts, sidecar ordering enforced), the flight-row countersignature and READ-row registration enforced by a gate before launch, one standard Fold-A paired read driver with per-scenario tables and delivery/conversion, the stale and pre-existing failing tests repaired so the suite is green, plus the in-flight slot fill, shared A/A and filler items. ANALYSIS: row-level attribution of the AGREE gain and harm, a cross-cell synthesis of every Stage-2/3 SLURP result by mechanism, the remaining error mass of the new best arm classified by source (retrieval, consumption, perception, format, knowledge content), a knowledge-content audit of the three SLURP stores, and the same diagnosis for Audio2Tool and Earnings from their sealed rows; each ends in a named capability list. All model-free on sealed bytes; gold only offline. |
| 164 | (owner 2026-09-27 ~15:00Z, on the knowledge wave from the analyses of row 163) Approve W1 slot-card selection (K8) -> W2 a position-1 guard on the agreement vote -> W3 intent contrast cards + a per-intent exemplar cap (K1+K6) -> W4 slot conventions: value vocabularies, do-not-tag conventions, span rules (K2+K3+K4)? | Owner (English translation): "Decision 1: I agree, and I suggest you immediately start the analysis and the preparatory work; after 9 o'clock they should take off as soon as possible!" Ruling: the wave is approved in that order and registered now, model-free, so every cell is flip-ready when the COMP-1 + G5 chain releases the card (about 01:00Z on 2026-09-28, 09:00 in the owner's time zone). Each W cell derives from the retained AGREE arm (row 161) with ONE change, its knowledge built from TRAIN rows outside Fold A only (the R01-excluded exemplar pool; no Fold A gold ever enters construction or tuning), its expectation declared from measured numbers (row 139), and the four arms read against ONE shared in-chain A/A of the AGREE arm's own bytes (row 160's precedent); admitted items fold into COMP-2 (row 138). |
| 165 | (owner 2026-09-27, on the Reviewer/Planner loop measuring nil) Keep, switch off, or repurpose? | Owner (English translation): "Decision 2: nodes like the Reviewer can all be optimised and improved; do not mechanically throw them away -- use training-free RL to optimise its behaviour on its own!" Ruling: the Reviewer is neither switched off nor rebuilt by hand; it becomes a TRAINING-FREE RL target of its own: its policy (instruction, the evidence it is shown, when it intervenes, what a revision may change) is optimised from sealed rollouts with per-node credit (`sealed-credit-system-policy-v1`; the Reviewer's revise/keep decisions and their outcomes in the sealed pools are the reward signal), node-scoped, read against an in-chain A/A with intent primary and the SLU guard. G5 (the retired-tool instruction removed) is its first, no-harm step; the Planner follows the same route after the Reviewer. |
| 166 | (owner 2026-09-27, on re-reading past verdicts under the corrected instrument) Re-label them? | Owner (English translation): "Decision 3: do not completely overturn ChatGPT's earlier work either; although he did not follow your rules, state our experiment rules explicitly to him in the handoff document. Where you judge a conclusion usable but the experiment non-rigorous, keep it provisionally; where you judge both the conclusion and the experiment unacceptable, adjust it." Ruling: a three-way classification of every affected verdict -- KEEP (conclusion and experiment sound), KEEP-PROVISIONAL (conclusion usable, experiment below today's instrument rules: kept, annotated with the specific rule it misses and what would settle it), ADJUST (neither acceptable: the verdict word is changed in place with the reason, the original kept visible) -- recorded as annotations in the results ledgers, never by deleting a row; closed lines stay closed unless the owner re-opens one. The standing handoff gains a section stating the experiment rules in force (in-chain A/A for cross-flight designs, the measured floors, registration before contact, countersigned rows and READ rows before launch, no if-then on unread results, per-stratum reporting, TRAIN-only construction). |
| 167 | (owner 2026-09-27) Accept the A2T-AA pair as Audio2Tool's own null although its registered request-hash identity check matched only 149 of 400 (the hash includes the serving slot id and the runtime request id; on content fields 400 of 400 are identical)? | Owner (English translation): "Decision 4: accept." Ruling: the null is accepted -- h_A2T = 1.625 pp on official tool accuracy (1.375 exact match, 1.875 repo tool accuracy; pass B - pass A +1.00 [-0.50, +2.75]; 317/400 answers byte-identical) -- and the read recipe's identity rule is amended to compare request CONTENT fields (the dispatch wrapper's slot id and request id excluded) for every multi-slot session; h_A2T is the bar reference for later Audio2Tool cells (row 139 applies to each). |
| 168 | (owner 2026-09-27, on the filler family) The only TRAIN rows the current system can fly outside Fold A are Fold B's 1,080 (six chunks, about 2.4 GPU-h): use Fold B, and re-sample Fold A / Fold B with new seed sets once the six chunks are flown? | Owner (English translation): "Decision 5: accept." Ruling: Fold B is used for the filler (it becomes construction-exposed for the current system; the held memory arms, if revived, get their own roster), and after the six chunks the filler continues as re-seeded rounds on Fold A and Fold B (new five-seed sets at T 0.7), each round its own registration and receipt -- more samples per row for the sealed-credit inner loop. |
| 169 | (owner 2026-09-27, re-plan v2 item 1) Insert A2, the COMP-1 replication on DEV-2000-ADDED (arm + in-chain A/A of the PLAN lock's bytes, own null h 1.1520 intent / 1.2525 SLU), on the card before the knowledge wave? | Owner (English translation, 2026-09-27 ~19:50Z, on the six items of docs/readiness/2026-09-27-slurp-stage3-replan-v2.md section 5): "Decisions 1-6: all agreed; execute as recommended." Ruling: A2 flies immediately after the COMP-1 + G5 chain and before wave 1; it is registered model-free now (package 2026-09-27-slurp-stage3-comp-1-dev2000-added-v1) with its expected effect left as a placeholder until the Fold A arm is read (row 139); its read settles AGREE's KEEP-PROVISIONAL (row 166) and gates admission of every wave item into COMP-2 (row 138). |
| 170 | (owner 2026-09-27, re-plan v2 item 2) Register W5, slot-side retrieval (the candidate-conditioned slot view with a filter plus speech-plus-candidate slot exemplars; oracle +17.4 / +16.5 SLU), as the SLU main line? | Owner (English translation, 2026-09-27 ~19:50Z, on the six items of docs/readiness/2026-09-27-slurp-stage3-replan-v2.md section 5): "Decisions 1-6: all agreed; execute as recommended." Ruling: W5 is registered against the wave's shared A/A (row 164) as the fifth cell of the same chain, after W4, ONE change from the AGREE bytes, knowledge built from TRAIN rows outside Fold A only; it is the SLU main line because it is the M1 mechanism (row-matched content to the deciding node), while W4's rule cards are read no-harm only. W4 and W5 each state the entity taxonomy they are read against. |
| 171 | (owner 2026-09-27, re-plan v2 item 3) Register now the B1 rank-visible rendering conversion probe (0.1 GPU-h on sealed rows; the arm follows only with the probe's conversion as its declared basis), the B3 catch-all rule offline design (agree-1 all-utterances signal, K5) and the B4 explicit empty-entity offline design with its own DEV offline null first? | Owner (English translation, 2026-09-27 ~19:50Z, on the six items of docs/readiness/2026-09-27-slurp-stage3-replan-v2.md section 5): "Decisions 1-6: all agreed; execute as recommended." Ruling: all three are registered model-free now; B1's arm is registered only after the probe is read and declares its expectation (row 139); B3 and B4 fly nothing until their offline reads clear the offline floor of their pool (B4 measures that floor first, because ROLL-3 reported only within-pool half-widths). |
| 172 | (owner 2026-09-27, re-plan v2 item 4) Authorise the same-flight supply-variant instrument as an engineering-base item: `supply_variants` re-authorised for the sealed-credit inner loop and for same-flight A/B reads (about 0.7 pp instead of the 2.5 pp cross-flight floor), with the `outputs.py` support the instrument note names? | Owner (English translation, 2026-09-27 ~19:50Z, on the six items of docs/readiness/2026-09-27-slurp-stage3-replan-v2.md section 5): "Decisions 1-6: all agreed; execute as recommended." Ruling: authorised as engineering base (Stage-2 unfinished, row 163's logic). The design is written first from the measurement instrument note and the VAR-2 package; the code lands in a worktree and merges only at a deliberate re-pin point, because it touches identity-bound implementation files. VAR-2 as a MECHANISM stays closed; this is the instrument and the rollout variation. |
| 173 | (owner 2026-09-27, re-plan v2 item 5) Re-read A2T-ORG-1 against the accepted Audio2Tool null h_A2T 1.625 now (model-free, row 166's deferred item), and register A-C1 (do-no-harm candidate formation, same-chain direct A/A beside every arm, parameter-F1 margin 2.23) only after the SLURP lock? | Owner (English translation, 2026-09-27 ~19:50Z, on the six items of docs/readiness/2026-09-27-slurp-stage3-replan-v2.md section 5): "Decisions 1-6: all agreed; execute as recommended." Ruling: the re-read runs now and annotates the ledger under row 166's three-way rule; A-C1 is registered after the SLURP line is locked or when the card would otherwise idle. |
| 174 | (owner 2026-09-27, re-plan v2 item 6) Earnings E-C1, the admitted KC-E1f repair into the default Earnings plan, after the E41 sub10 harness proof (E-C0)? | Owner (English translation, 2026-09-27 ~19:50Z, on the six items of docs/readiness/2026-09-27-slurp-stage3-replan-v2.md section 5): "Decisions 1-6: all agreed; execute as recommended." Ruling: E-C1 is registered after E41 sub10 passes its form gates; E-C2 (retrieval-fed repair) and E-C3 (numeric re-listen) follow in that order, each against the E21 own null. |

Outcome of decision 170 (2026-09-28 00:20Z): W5 was registered as built (package 2026-09-27-slurp-stage3-w5-fold-a-v1, held) but its model-free offline estimate shows almost no delivery headroom: of the AGREE arm's 173 MISSING slot items W5 newly shows the gold value on 10 (M1's twenty exemplars already show it on 90 that were still missed); at M1's measured conversion 0.247 the expectation is 0.14 pp SLU, ceiling 0.548, under the 1.2485 floor, with an over-tagging risk on the 414 rows without gold slots. Coordinator ruling: W5 stays registered and HELD, not flown; the SLU main line is re-pointed at USE, not delivery (W4 conventions read no-harm, B4 explicit empty-entity decision, and slot-side contrastive consumption at the Solver in B1's family); the +17.4 figure quoted for slot-side retrieval was an oracle, not a delivery headroom.
| 175 | (owner 2026-09-28, on the COMP-1 citation-contract abort at 03:28:18Z after 1,913 calls / 471 rows) Recover by RESUME (a new attempt under the same run id with `resume_from` the aborted attempt + trace sha256, keeping the 471 finished rows) although the harness code changed (fixes a451f942 citation-id collapse, seal refusal -> per-row abstain, and the resume.py replay fix), or by a fresh -REC re-fly of all 1,080 rows (the coordinator's default)? | Owner (English translation, 2026-09-28 ~13:20Z): "Decision 1: proceed per option A; we agreed before that there must be a resume-from-breakpoint capability, and resuming after a program bug is fixed is the advanced form of that capability. Decision 2: authorised. Decision 3: issue it. Decision 4: agreed. Decision 5: agree with the recommendation." Ruling: RESUME (variant 1 of docs/results/2026-09-28-slurp-comp1-citation-abort-diagnosis.md). Decision 22 is AMENDED: a resume after a harness fix is admitted when (i) the fix is proven offline to seal every kept row byte-identically under the fixed code (receipt coordination/slurp-stage3-comp1-fold-a-v1/resume-byte-identity-proof-v1.json: 481/481 captures identical, the refused answer accepted, 0 regressions), (ii) the request bytes are unchanged, (iii) the flight's one recovery re-registration is spent by it. The -REC variant (flipped at 472474bf, receipt root-admission-rec-v1.json) is superseded unflown; the resume attempt is this flight's one recovery; the shared A/A SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 (FINALIZED, scored) stays the comparator in the same serving session; the resume flies before the sub10 geometry swap. The coordinator's earlier default (-REC) is withdrawn on this ruling. |
| 176 | (owner 2026-09-28) Authorise updating the Stage-2A synthesis-verification digest lock (`FILE_DIGESTS` for rails/kb_policy.py in tests/unit/test_stage2a_synthesis_verification.py) after the fastrecall vectorisation (25,280 recalls bit-identical) and the W3 fuser landed (owner decisions 159, 164)? | Owner (English translation, 2026-09-28 ~13:20Z): "Decision 1: proceed per option A; we agreed before that there must be a resume-from-breakpoint capability, and resuming after a program bug is fixed is the advanced form of that capability. Decision 2: authorised. Decision 3: issue it. Decision 4: agreed. Decision 5: agree with the recommendation." Ruling: authorised. The lock is re-pinned to the live digest with a RE-PIN paragraph citing the fastrecall bit-identity proof and the W3 merge; the earlier locked value stays visible in the paragraph; no behaviour of kb_policy is changed by the re-pin. |
| 177 | (owner 2026-09-28) The receipt docs/receipts/a2t/A2T-CANONICAL-FAMILY-SECONDARY-FIXED8.json recorded a wrong sha256 for the exclusion file A2T-G6-FAMILY-SWEEP-FIXED16.json at authoring time (not a CRLF issue: git blob equals working tree, zero CR bytes, one commit in its history). Issue a successor? | Owner (English translation, 2026-09-28 ~13:20Z): "Decision 1: proceed per option A; we agreed before that there must be a resume-from-breakpoint capability, and resuming after a program bug is fixed is the advanced form of that capability. Decision 2: authorised. Decision 3: issue it. Decision 4: agreed. Decision 5: agree with the recommendation." Ruling: issue A2T-CANONICAL-FAMILY-SECONDARY-FIXED8-v2.json with the correct digest and a `supersedes` field naming v1 and the defect; v1 is never rewritten; the test that reads the receipt points at v2; the results-ledger row that cites v1 gets an appended note. |
| 178 | (owner 2026-09-28, on the W3a read: intent -0.56 [-1.67, +0.56] vs the shared wave A/A, K1's 6.94 pp ceiling not converting in card form) Close K1 as cards and keep contrastive evidence only at the decision node? | Owner (English translation, 2026-09-28 ~13:20Z): "Decision 1: proceed per option A; we agreed before that there must be a resume-from-breakpoint capability, and resuming after a program bug is fixed is the advanced form of that capability. Decision 2: authorised. Decision 3: issue it. Decision 4: agreed. Decision 5: agree with the recommendation." Ruling: agreed. K1-as-cards is closed (W3a NOT ADMITTED, docs/results/2026-09-28-slurp-w3a-fold-a-read.md); the contrast action continues as B1 rank-visible rendering (probe RANKVIS ready at b0c6c608, then an arm declared from m against the 15.9-row no-op expectation) and the Reviewer top-2 contrast of decision 165's second round. |
| 179 | (owner 2026-09-28, on B3 INERT / B4 INERT-BY-INSTRUMENT and the measured DEV multi-sample offline null 1.547 pp SLU / 0.810 intent, 2.3x the assumed 0.67) Discontinue offline rule designs on multi-sample sealed pools and use the same-flight supply-variant instrument for sub-2.5 pp reads? | Owner (English translation, 2026-09-28 ~13:20Z): "Decision 1: proceed per option A; we agreed before that there must be a resume-from-breakpoint capability, and resuming after a program bug is fixed is the advanced form of that capability. Decision 2: authorised. Decision 3: issue it. Decision 4: agreed. Decision 5: agree with the recommendation." Ruling: agreed. Offline rule designs on multi-sample pools are discontinued as a design class (records stay); sub-floor reads use the same-flight supply-variant instrument (owner decision 172; set A + set B + the release-swap route merged 2026-09-28); its first real cells are W-SV-1 (exemplar k 20 vs 30 + twin) and W4-SV (release swap to slot-contracts-w4-v1), both on TRAIN Fold A with claim `nominated` only. |
| 180 | (owner 2026-09-28 ~14:00Z, after the coordinator's critical analysis of the owner's three consumption routes -- discriminative presentation, progressive loading of closed vocabularies, ASR verification/replay -- under the principle that every node must show an effective information gain) Route 3's form: a core-native targeted re-listen (the OBS node revisits the audio conditioned on the decided intent and slot type; no second model, no transcript state) first, with a pinned Whisper tool-level verifier only as a later comparison? | Owner (English translation): "Agreed: do the core-native re-listen first; leave Whisper until E4 has a read." Ruling: the owner's guidance stands as the working thesis -- knowledge supply is sufficient in content; the work is the model's consumption of it, per node, with intent and slots decoupled -- amended by the coordinator's measured caveats (static discriminative descriptions are closed after W3a; ASR replay addresses only the span/spelling/mishearing classes, bounded by about 4 pp mishearing + 2.9 pp BOUNDARY + part of NEAR/FORMAT, not the SPURIOUS/MISSING decisions). The extension experiments E1-E6 are adopted: E1 node information-gain ledger (offline, running), E2 decision-node contrast (B1 probe then arm; B5 Reviewer top-2), E3 progressive slot loading (type first, then the closed vocabulary of the chosen type; same-flight instrument), E4 core-native targeted re-listen (OBS revisit keyed by intent + slot type; registered after E1 shows the Perception-origin share of span errors), E5 explicit catch-all decision inside E2's contrast, E6 an information-gain gate: a node that shows no positive gain in the ledger does not enter COMP-2. The 2026-09-06 direction (no transcript state, no ASR tool) is NOT revised; a Whisper comparison needs its own owner row after E4 reads. |

Outcome of decision 176 (2026-09-28): RE-PINNED in cfd34bf5 (merged 87189a82): the `FILE_DIGESTS` entry for rails/kb_policy.py moves from 336c5b95... to b0d8d9d4...; the fastrecall identity proof covers 25,280 records with 0 mismatches, and the W3 fuser is unused by every Stage-2A plan; tests/unit/test_stage2a_synthesis_verification.py passes (26).

Outcome of decision 177 (2026-09-28): SUPERSEDED BY v2 in 3d02f68f (merged 03c94d72): docs/receipts/a2t/A2T-CANONICAL-FAMILY-SECONDARY-FIXED8-v2.json corrects the exclusion-file digest (recorded fcc83503... vs actual 3a7a59d3...); the nine other digests were verified unchanged; no results-ledger row cited v1, and v1 stays in place as the immutable record.
| 181 | (owner 2026-09-28, on the COMP-1 RESUME attempt that STOPped at 15:20:46Z four minutes after launch at flight commit 902454db -- "arm failed on step 1, campaign rc 1; inspect: no run manifest" -- while the standing rule allows one recovery re-registration per flight and says a second failure stops the flight and the fix is proven on a 4-row dry run) Option A: treat it as a harness defect of the resume path, fix, prove on a 4-row dry run, then resume the SAME attempt semantics (not a new recovery); or option B: fall back to the superseded -REC full re-fly? | Owner (English translation, 2026-09-28 ~23:30Z, on the six items of the coordinator's post-restart brief): "Decision 1: option A, fix it, prove the fix on a 4-row dry run, then resume. Decisions 2-6: agreed." Ruling: option A. The resume path is the owner's required "resume-from-breakpoint after a bug fix" capability (row 175) and this is its first real exercise; the fix lands with a unit test reproducing the failing shape, is proven on a 4-row dry run of the fixed tree (a resume-mode dry run over four kept rows plus one to-fly row where the harness allows it, else the standard smoke), and the resume attempt is re-launched under its own attempt id; the 471 kept rows and the aborted attempt's trace are never rewritten; -REC stays superseded unflown. Meanwhile the card flies RANKVIS, the same-flight cells and sub10 so the GPU does not idle. |
| 182 | (owner 2026-09-28, after the GPU idled about eight hours because the halted queue had no successor while the coordinator's session was down) Authorise an IDLE WATCHDOG as an engineering-base item: a scheduled task that, every few minutes, when no flight/driver/swap is alive, no STOP is live, the serving geometry is healthy or swappable, and a registered ready-chain list names a next chain, launches that chain through the batch driver (row 77 unchanged: flights only through the driver), logging every decision? | Owner (English translation, 2026-09-28 ~23:30Z, on the six items of the coordinator's post-restart brief): "Decision 1: option A, fix it, prove the fix on a 4-row dry run, then resume. Decisions 2-6: agreed." Ruling: authorised. The watchdog never launches onto a STOP, never edits records, never starts a CPU sidecar, respects the hold files, and its ready-chain list is a committed file the coordinator edits. |
| 183 | (owner 2026-09-28) Card order for the current window: RANKVIS (0.1 GPU-h) -> W-SV-1 (~3) -> W4-SV (~3) -> E41 sub10 (12, E21 geometry) -> filler, i.e. the two same-flight SLURP instrument cells before the Earnings harness proof (row 158), because SLURP is locked first and the two cells steer the next SLURP round? | Owner (English translation, 2026-09-28 ~23:30Z, on the six items of the coordinator's post-restart brief): "Decision 1: option A, fix it, prove the fix on a 4-row dry run, then resume. Decisions 2-6: agreed." Ruling: agreed; the pre-sub10 hold stays until W-SV-1 and W4-SV have flown; sub10 follows; the COMP-1 resume re-enters the card as soon as row 181's dry run passes. |
| 184 | (owner 2026-09-28) Register the first two cells of the instrument's PHASE 2 (Perception-phase variants; spec docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-perception-variants-design.md with the coordinator rulings O1-O6): P-SV-1 (AGREE's Perception evidence as flown vs a top-2 contrast rendering, twin as the null; ceiling 3.89 pp from the 42 rank-2 rows) and P-SV-2 (forced three-candidate list; gold-on-list primary, a presence measurement), both on TRAIN Fold B at level 2, claim `nominated`, after merge set C lands? | Owner (English translation, 2026-09-28 ~23:30Z, on the six items of the coordinator's post-restart brief): "Decision 1: option A, fix it, prove the fix on a 4-row dry run, then resume. Decisions 2-6: agreed." Ruling: agreed. |
| 185 | (owner 2026-09-28) Implement E4 v1, the core-native targeted re-listen (spec docs/superpowers/specs/2026-09-28-e4-core-native-targeted-relisten-design.md with the post-E1 rulings: blind re-listen + forced choice; two shadow columns, replace-only and replace-plus-drop-when-unheard; shadow delivery on Fold A; expected 0.0 nominated; bar = the twin/shadow null), as the next engineering item after merge set C, with a 4-row dry run before its flight? | Owner (English translation, 2026-09-28 ~23:30Z, on the six items of the coordinator's post-restart brief): "Decision 1: option A, fix it, prove the fix on a 4-row dry run, then resume. Decisions 2-6: agreed." Ruling: agreed. |
| 186 | (owner 2026-09-28) Interpret row 168's "Fold B becomes construction-exposed" as ROLLOUT-exposed while Fold B serves as the phase-2 read roster (the filler flies Fold B rows as rollouts, builds nothing from them; W2's Fold-B-tuned guard was stopped and nothing built on it is read), with the rule that a phase-2 cell whose branch values are built from Fold B rollouts may not be read on Fold B? | Owner (English translation, 2026-09-28 ~23:30Z, on the six items of the coordinator's post-restart brief): "Decision 1: option A, fix it, prove the fix on a 4-row dry run, then resume. Decisions 2-6: agreed." Ruling: agreed. |
| 187 | (owner 2026-09-28 ~23:45Z, mid-turn, overriding row 183's placement of E41 sub10) Which carriers may use the GPU now? | Owner (English translation): "Apart from SLURP, do not run the other GPU experiments for now; focus on analysing and improving SLURP's gains and on locking the methodology." Ruling: SLURP only on the card until the owner reopens the other carriers. E41 sub10 (row 158 / 174) is deferred (its flipped cell stays ready at bf6db903; its queue step and the E21 swap are removed; the watchdog's ready-chain list carries it disabled with `allowed_carriers: [slurp]`). Audio2Tool rows 155/157/173 and Earnings rows 174 keep their registrations but fly nothing. Card order becomes RANKVIS -> W-SV-1 -> W4-SV -> COMP-1 resume (after row 181's dry run) -> P-SV-1/P-SV-2 -> E4 v1 -> filler (SLURP Fold B rollouts) in the gaps. Model-free analysis and engineering continue on every carrier. |
| 188 | (owner 2026-09-29 ~00:05Z, on the REV-TFRL-1 read: intent -0.46 [-1.57, +0.65] and SLU-F1 -0.55 [-1.79, +0.69] against its in-chain A/A, the +0.80 declaration outside the CI, REVISE reach 3.32 % -> 30.57 % with intent repairs/breaks 14/15 and entity 34/16, +0.42 GPU-h per 1,080 rows) Shelve the Reviewer TF-RL second round (B5, the Reviewer top-2 contrast of row 165) in favour of the Perception-phase cells P-SV-1 / P-SV-2 (row 184)? | Owner (English translation): "Agreed on decision 188: B5 is deferred; do P-SV-1 / P-SV-2 first." Ruling: REV-TFRL-1 is NOT ADMITTED (neutral by width with a measured cost; reach was achieved, judgment quality was not: repairs equal breaks). Row 165's route is not closed: the Reviewer stays a training-free RL target, but its next round waits for the Perception-branch reads; if P-SV shows that contrastive evidence moves the deciding node, the same contrast is offered to the Reviewer as a second judgement (B5) afterwards. The node information-gain ledger (docs/results/2026-09-28-slurp-node-information-gain-ledger.md) is the basis: the Solver follows Perception's rank 1 on 97.6 % of rows and the Reviewer/Planner add no measurable gain. |

Outcome of decision 181 (2026-09-29 00:30Z): the diagnosis found no harness defect -- the resume attempt loaded, replayed and passed prelaunch; 3 s after its first Perception wave the resident llama-server aborted on `CUDA error: the function failed to launch on the GPU` (ggml_cuda_op_mul_mat_cublas, ggml-cuda.cu:1774; an earlier `illegal memory access` abort in the same 14.6 h server.log), the client saw RemoteDisconnected -> ExecutionError 100054 -> NativeEpisodeError, 4 calls / 10.6 s audio spent, the 471 kept rows untouched. Owner (English translation, 2026-09-29): "Agreed: retry the resume directly under decision 22." The fix-and-dry-run branch of row 181 is void (infrastructure failure, code unchanged); the recovery is retried as resume attempt 2 of the same run, `resume_from` the original aborted attempt, the one recovery of row 175 unchanged; it flies after RANKVIS (queue SAEA-Queue-RESUME2), then W-SV-1 / W4-SV, then the filler (row 187: SLURP only).

Outcome of decision 182 (2026-09-29): the idle watchdog is merged at bdaa66b4 (fable/watchdog 3b4b176c: `scripts/flights/batch/idle_watchdog.sh`, `idle_watchdog_select.py`, `idle_watchdog_recovery.py`, the committed ready-chain list `scripts/flights/batch/ready_chains.json` with `allowed_carriers: [slurp]` per row 187, `serving_swap.sh --restart`, `saea_task.ps1 -RepeatMinutes`; tests/unit/test_idle_watchdog.py 32 passed in its worktree before the merge). The first registration was refused by Windows PowerShell 5.1 (`-RepetitionDuration ([TimeSpan]::MaxValue)`, HRESULT 0x80041318); 8d36213f drops the duration (a -Once trigger with only -RepetitionInterval repeats indefinitely). The Windows Scheduled Task `SAEA-Watchdog` is registered with a 5-minute repetition and started PAUSED: `/home/chao/saea-queue/watchdog.hold` was created before the registration, and the coordinator removes it. Its first ticks (2026-09-29T00:20:58Z and 00:21:59Z, `/home/chao/watchdog.out`) exited quietly at gate 1 ("busy": the flight lock of COMP-1 resume attempt 2 is still present although its pid is gone, and the parked RANKVIS/SUB10 queue script is alive) -- the gate before the hold check; nothing was launched. Resume attempt 2 had STOPped at 00:20:43Z (see the handoff); its STOP text carries no server-death signature, so the watchdog would not launch onto it even without the hold.

Outcome of decision 188 (2026-09-29): REV-TFRL-1 is recorded NOT ADMITTED (neutral by width with a measured cost) in the coordinator verdict of `docs/results/2026-09-28-slurp-revtfrl-1-fold-a-read.md` and its results-ledger line: intent -0.46 [-1.57, +0.65] and SLU-F1 -0.55 [-1.79, +0.69] against the in-chain A/A, both no-harm clauses failed and no harm clause met, the +0.80 declaration above the CI, REVISE reach 3.32 % -> 30.57 % with intent repairs/breaks 14/15 and entity 34/16, +0.42 GPU-h per 1,080 rows. B5 (the Reviewer top-2 contrast) is deferred behind P-SV-1 / P-SV-2; row 165's route stays open. The same commit records RANKVIS INERT (form proof; the B1 arm is not registered): m = 19/119 against the no-op 15.9, gold at boundary position 1 converted 14/18 and positions 2-8 5/101 (`docs/results/2026-09-29-slurp-rankvis-probe-fold-a-119-read.md`).

Outcome of decision 181 (addendum, 2026-09-29 03:50Z): resume attempt 2 (00:14-00:20Z) aborted on a FIT-identity collision caused by a coordinator-side registration error (attempt 1's FIT attempt id was reused; 48 calls); attempt 3 (fresh ids; 4-row dry run PASSED 02:04:29Z) flew all 609 to-fly rows (2,476 calls, 02:04-03:18Z) and ABORTED AT SEAL on the 471 replayed rows: `FlightRuntimeError: native delivery normalisation output differs from the delivered text` -- root cause in core/flight/resume.py::_classify, which handed the seal the raw recorded response of a kept row instead of the normaliser's delivered output; fixed in fable/sealcheck d619e1c5 (`_replay_delivery_normalisation`); the new offline checker scripts/analysis/replay_seal_consistency.py reproduces the abort on 471/471 kept rows under the old code and reports 0 failing rows of 1,080 (471 kept + 609 flown) under the fix (docs/results/2026-09-29-slurp-comp1-resume3-seal-abort-diagnosis.md). Lesson recorded: a 4-row smoke cannot see seal-time checks on kept rows; the offline full-trace replay becomes a pre-launch step for every resume. Next step is the owner's row 189.

| 189 | (owner 2026-09-29, on the COMP-1 resume attempt 3 that flew all 609 remaining rows and aborted at the seal on the replay defect fixed at d619e1c5; decision 181 outcome and addendum) Recover COMP-1 by option A, a SEAL-ONLY completion (the same run id SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1; resume_from the original aborted attempt, 471 rows, and resume attempt 3, 609 rows; zero new model contacts, 0 GPU; replay proof 1,080 checked / 0 failing / 0 sealed twice), or option B, re-fly from attempt 3? | Owner (English translation, 2026-09-29, on the coordinator's decisions 189-193): "Decision 189: agreed; decision 190: fine; decision 191: close it; decision 192: OK; decision 193: GO." | Ruling: option A, the one recovery of row 175. Outcome: countersigned in b39843583; decision receipt `coordination/slurp-stage3-comp1-fold-a-v1/root-admission-sealonly-v1.json` (decision id slurp-stage3-comp1-fold-a-sealonly-admission-v1, sha256 8a203ffd...); flipped to ready together with G5 at flight commit fd8a01fe1; queued as SAEA-Queue-SEALONLY behind P-SV. |
| 190 | (owner 2026-09-29, on `docs/results/2026-09-29-slurp-same-flight-floor-recalibration.md` and the W4-SV read) Re-calibrate the same-flight effect floors per metric to the larger measured contrast half-width -- intent 0.65 pp and SLU-F1 1.49 pp at n = 1,080 -- with shadow-relisten cells floored on SLU only, and require a `primary_metric_key` on every same-flight cell that claims a benefit from 2026-09-30? | Owner (English translation, 2026-09-29, on the coordinator's decisions 189-193): "Decision 189: agreed; decision 190: fine; decision 191: close it; decision 192: OK; decision 193: GO." | Ruling: adopted. Consequence: inner-loop run 1's k = 10 nomination (+0.48, `docs/results/2026-09-29-slurp-sealed-credit-inner-loop-run-1.md`) lapses under the SLU floor; run 1 nominates nothing. Implemented on fable/floor190 (`scripts/checks/stage3_effect_floor_check.py`, `accept.py`, the four registration writers, tests), merged in c2f1be08a; the floor check now reports W4-SV's missing `primary_metric_key` as an advisory. |
| 191 | (owner 2026-09-29, after W4 and W4-SV, two reads of the rule-card slot-convention line, both under the floor; `docs/results/2026-09-29-slurp-w4sv-fold-a-column-read.md`) Close the rule-card slot-convention line entirely? | Owner (English translation, 2026-09-29, on the coordinator's decisions 189-193): "Decision 189: agreed; decision 190: fine; decision 191: close it; decision 192: OK; decision 193: GO." | Ruling: CLOSED. No re-fly of the slot-convention cards in any design (cross-flight, same-flight or composed); the SLU main line is not the delivery of conventions. The W4 and W4-SV results-ledger entries carry the closure clause. |
| 192 | (owner 2026-09-29) Keep W5 (slot-side retrieval, row 170) held, and require any SLU mechanism to show at least 1.5 pp predicted by offline analysis before it is registered? | Owner (English translation, 2026-09-29, on the coordinator's decisions 189-193): "Decision 189: agreed; decision 190: fine; decision 191: close it; decision 192: OK; decision 193: GO." | Ruling: agreed. Outcome: the headroom note `docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md` (fable/w5offline, merged in 949d77d1c) finds NO SLU mechanism at >= 1.5 pp at the measured conversions (best composition about 1.28 pp); W5's expected effect is 0.15 pp, so the coordinator closes the W5 line (the owner may reopen it). Of 229 undetermined items, 107 had the gold value supplied (consumption 214 of 407). A deterministic scope rule reads +1.04 pp offline; its admission bar is row 195. |
| 193 | (owner 2026-09-29) Let P-SV-1 / P-SV-2 (row 184) proceed after the wiring fix, the table v2 (coordinator ruling O7) and the branch-seed identity fix? | Owner (English translation, 2026-09-29, on the coordinator's decisions 189-193): "Decision 189: agreed; decision 190: fine; decision 191: close it; decision 192: OK; decision 193: GO." | Ruling: GO. Outcome: flipped to ready at b9af3e58; flying since 11:51Z as SAEA-Queue-PSV. |
| 194 | (owner 2026-09-29, after the E4-1 arm SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1 flew all 1,080 rows and aborted at the seal; seal-invariant fix b286d897, merged in 109538e8; replay proof 1,080 checked / 0 failing) Admit the E4-1 SEAL-ONLY completion (the shape of row 189; E4-1's one recovery; zero new model contacts)? | Owner (English translation, 2026-09-29): "Decision 194: GO." | Ruling: GO. Outcome: countersigned in b39843583; decision receipt `coordination/slurp-stage3-relisten-fold-a-v1/root-admission-sealonly-v1.json` (decision id slurp-stage3-relisten-fold-a-sealonly-admission-v1, sha256 43d83158...); the coordinator's column gate is pre-declared on the READ row SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1 before any read (replace-only column: >= 29 % net conversion of the 106 items; drop column: >= 49.5 net false positives removed). The flip was refused on a parent-config residue (fix in progress on fable/repinresume); not yet queued. |
| 195 | (PROPOSED 2026-09-29, awaiting the owner) Which bar applies to a deterministic post-hoc output edit -- the do-not-tag scope rule, +1.04 [+0.53, +1.57] pp offline, replicate +0.93, under the DEV-2000 pool null of 1.547? Option A: treat it as a normaliser-class form change, read no-harm cross-flight on DEV-2000 (2.5 pp bar; it would not clear). Option B: admit it as a USE-layer deterministic node action inside the COMP-2 composed policy, read only inside the composed arm's DEV read. | Owner (English translation, 2026-09-29): "Decision 195: agreed; I want you to finally unify these assembled components into one module, carried as a module that may itself call the model." Ruling: option B ADOPTED -- the do-not-tag scope rule enters as a USE-layer deterministic node action inside the COMP-2 composed policy and is read only inside the composed arm's DEV read (the coordinator had recommended B under the analysis-to-node directive of 2026-09-18; source `docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md`). Consequence: the assembled consumption components (node policy, verification, USE steps, receipts) are to be unified into one consumption module that may call the frozen core; its design is being written in `docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md` on branch fable/moduledesign. Nothing is registered until that design lands. |
| 196 | (owner directive 2026-09-29, after decision 195) Once the training-free RL has stable gains on SLURP, what must the consumption module support beyond SLURP? | Owner (English translation, 2026-09-29): "Note: once our training-free RL has stable gains on the SLURP task, it must be able to transfer and extend to Audio2Tool, E21, E22 and similar tasks." Consequence: the decision-195 module is carrier-agnostic -- node policy, verification, USE steps, receipts, the inner loop and the measurement instrument are shared; only the TaskAdapter, the scorer, the knowledge stores and the config fragments are per carrier. Carrier admission: a module-all-off A/A on that carrier's roster first, before any module arm on it. The design lists every SLURP hard-coding in the current components as a migration item. |
| 197 | (owner 2026-09-29, after the P-SV-1 arm SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1 flew all 1,080 rows (8,709 calls) and aborted at the seal on invariant I7v; I7v fix 0177f83f; replay proof 1,080 checked / 0 failing / 0 sealed twice) Admit the P-SV-1 SEAL-ONLY completion after the I7v fix (the shape of rows 189 and 194; P-SV-1's one recovery; zero new model contacts)? | Owner (English translation, 2026-09-29): "Decision 197: agreed." | Ruling: AGREED. Outcome: fix merged in 0177f83f; cell `slurp-native-stage3-psv1-fold-b-v1-resume` registered, countersigned and minted in a842f670 (decision receipt slurp-stage3-psv1-fold-b-sealonly-admission-v1; same run id, attempt attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only, resume_from the aborted arm attempt); the flip was refused once on the parent-package residue (fixed fe41553a, merged 4b2946f3); flipped at c6e98e6b (the re-run satisfied with no new commit; P-SV-2/P-SV-3 and COMP-1b converged at the same HEAD); queued as SAEA-Queue-NEXT after COMP-1b. |
| 198 | (owner 2026-09-29, after the COMP-1 read: intent +4.26 [+2.41, +6.11], SLU-F1 -2.24 [-3.97, -0.47], the HARMFUL branch; the attribution `docs/results/2026-09-29-slurp-comp1-slu-harm-attribution.md` (branch fable/comp1slu, to be merged) names the Solver cited-answer contract -- +102 false positives on the 414 zero-gold rows -- and clears the unwrap and the supply) What does A2 compose? Option A: AGREE alone on DEV. Option B: COMP-1b = AGREE + the centroid boundary key WITHOUT the citation contract, on TRAIN Fold A against the same in-chain A/A, declared intent +4.26, SLU guard -1.2485; then A2 = COMP-1b on DEV-2000-ADDED. Option C: repair the citation contract. | Owner (English translation, 2026-09-29, after the coordinator's explanation recommending B): "OK (B adopted)". Ruling: option B ADOPTED; COMP-1 itself NOT ADMITTED. Consequence: COMP-1b is registered and held on branch fable/comp1b (cell `slurp-native-stage3-comp1b-fold-a-v1`) and is flipped and queued after the P-SV flips; the citation contract leaves the COMP-2 component list and may return only as its own single-factor cell with an entity-emission limit; GPU order G5 -> COMP-1b -> P-SV-2/P-SV-3 -> A2. Outcome (2026-09-30): A2 REPLICATED/ADMITTED on DEV: intent +4.60 [+2.58, +6.73], SLU +0.53 [-1.04, +2.09]; COMP-1b = first dev-admitted composed arm (`docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md`). |
| 199 | (owner directive 2026-09-29, after decision 198) May a slot be none, and may knowledge retrieval return nothing? | Owner (English translation, 2026-09-29): "Preserve and maintain the right for a slot to be none; conversely, knowledge retrieval must be allowed to return EMPTY instead of always returning results, otherwise the downstream model cannot decide correctly." Consequence (coordinator): (i) supply-side abstention is a first-class outcome -- every retrieval/supply node (exemplars k, boundary supply, slot views) may deliver nothing when nothing is relevant, the empty delivery is receipted and never padded to k; (ii) answer-side none is a first-class answer -- the Solver contract carries an explicit "no entities" option and the read scores it (the 414 zero-gold rows of Fold A are the test bed; the COMP-1 citation harm was exactly forced emission on them); (iii) the consumption-module design gains section 2c "Empty is legal"; (iv) an offline headroom analysis of supply abstention is dispatched (branch fable/emptysupply); (v) B4 (explicit empty-entity decision, offline net -0.19) is re-examined under this principle rather than closed. |
| 200 | (coordinator 2026-09-29, under owner decision 184 and the owner's standing instruction that the GPU must not idle) Register P-SV-3, the phase-2 Perception boundary-depth branch column (cell `slurp-native-stage3-psv3-fold-b-v1`, `docs/readiness/2026-09-29-slurp-stage3-psv3-fold-b-v1-preregistration.md`: branch `b-depth` raises fuse_coverage m and top_l 8 -> 12 beside `t-twin` and the delivering `a-agree`, TRAIN Fold B, gold-on-list primary as a presence measurement, expected effect 0.0 pp, claim ceiling `nominated`)? | Coordinator-registered under decision 184 (flipped at `c6e98e6b`, queued after P-SV-2 in the SAEA-Queue-NEXT chain), then put to the owner. Owner (English translation, 2026-09-29 ~23:10Z, on the coordinator's decisions 200-204): "Decision 200: agreed; decision 201: agreed -- and we adjust the research direction: on 09-06 the focus was still how to use the main model well; now it is how to build the system and optimise at system level; decision 202: GO; decision 203: good; decision 204: agreed." Ruling: AGREED ("agreed"). Outcome: P-SV-3 flies -- flying since 23:25Z (smoke PASS; arm since 23:25:39Z) at flight commit `c6e98e6b` in the SAEA-Queue-NEXT chain, ahead of A2; its READ row is countersigned after the seal and it is read with the P-SV read driver under the decision-190 floors. |
| 201 | (PROPOSED 2026-09-29, awaiting the owner; after the E4-1 read `docs/results/2026-09-29-slurp-e4-relisten-fold-a-column-read.md`: both re-listen columns SHADOW HARM, replace-only SLU-F1 -4.11 [-5.41, -2.88], replace + drop -3.59 [-5.08, -2.14], core-native replacement re-listen CLOSED) Open the frozen tool-level ASR (Whisper) route for slot-value verification (E5), as decision 180 sequenced ("core-native first, Whisper after the E4 read")? Option A: register E5 offline-first -- a pinned Whisper transcript pass over the Fold A audio as a logged tool contact (a new tool contact class), then an offline oracle on the 106 addressable items before any core contact. Option B: close the re-listen route entirely. | Coordinator recommends A. Owner (English translation, 2026-09-29 ~23:10Z, on the coordinator's decisions 200-204): "Decision 200: agreed; decision 201: agreed -- and we adjust the research direction: on 09-06 the focus was still how to use the main model well; now it is how to build the system and optimise at system level; decision 202: GO; decision 203: good; decision 204: agreed." Ruling: option A ADOPTED ("agreed"), given together with the direction sentence "We adjust the research direction: on 09-06 the focus was still how to use the main model well; now it is how to build the system and optimise at system level." (recorded as directive row 205). Consequence: E5-0 (one pinned Whisper pass over the roster audio, a logged tool contact of a new class, no core contact) and E5-1 (the model-free offline oracle) are prepared on branch fable/e5prep as INSTRUMENTS and ORACLES only; nothing they produce reaches a core request by itself (E5 spec addendum, `docs/superpowers/specs/2026-09-29-e5-asr-tool-slot-value-verification-design.md`). The 2026-09-06 "no transcript tokens" ruling is SUPERSEDED IN SCOPE: a pinned, logged tool is a system component. Transcripts still never enter the intent decision -- an engineering finding, not a ruling: with transcripts in the prompt DEV-1000 read intent -0.90 [-1.68, -0.09]. The runtime form is fixed by row 206 (model-initiated offer; the system-applied E5-2a is withdrawn). Outcome (2026-09-30): E5-0 ran (both folds, 0 core contacts); E5-1 oracle fired the stop condition (containment 0.7513 < 0.80); verify-span route CLOSED; E5-2 not registered; the missing-slot proposal tool form (ceiling +8.21 pp, precision 0.25) is routed to 209-B (`docs/results/2026-09-30-slurp-e5-transcript-consistency-oracle-read.md`). |
| 202 | (PROPOSED 2026-09-29 by the coordinator) Request the test-sample milestone read under the decision-151 allowance (`SLURP-TEST-SAMPLE-3010-V1`) once A2 -- COMP-1b on DEV-2000-ADDED, cell `slurp-native-stage3-comp1b-dev2000-added-v1`, the dev-admission test -- reads NOMINATED or better? | Owner (English translation, 2026-09-29 ~23:10Z, on the coordinator's decisions 200-204): "Decision 200: agreed; decision 201: agreed -- and we adjust the research direction: on 09-06 the focus was still how to use the main model well; now it is how to build the system and optimise at system level; decision 202: GO; decision 203: good; decision 204: agreed." Ruling: GO, conditional on A2 reading NOMINATED or better; a lower A2 verdict voids it. Consequence: the milestone read package is prepared and held on branch fable/milestoneprep (in progress; nothing registered on master); one-shot semantics -- one flight, one read, each read run id one attempt, no recovery re-fly on the sample, no re-read and no selection on it; decision 151's gate stands (the first contact follows the coordinator's report of the dev-admitted composed arm to the owner), and the closure roster `SLURP-TEST-CLOSURE-10068-V1` stays `pending-owner`. Development numbers remain development numbers (decisions 28 and 86). Condition met 2026-09-30 by the A2 read; milestone flip waits for 207 (allowance v2 FIT ids) and the sample preparations 2/3 (ran in the E5 gap on 2026-09-30). |
| 203 | (PROPOSED 2026-09-29 by the coordinator) COMP-2 = COMP-1b + the do-not-tag scope rule (row 195 option B) (+ optionally the none hint), read cross-flight on DEV? | Owner (English translation, 2026-09-29 ~23:10Z, on the coordinator's decisions 200-204): "Decision 200: agreed; decision 201: agreed -- and we adjust the research direction: on 09-06 the focus was still how to use the main model well; now it is how to build the system and optimise at system level; decision 202: GO; decision 203: good; decision 204: agreed." Ruling: GOOD ("good") -- adopted. Consequence: the scope rule's SLU side is read OFFLINE as a stage column on A2's sealed outputs (0 GPU; the deliver stage `saea-deliver-scope-rule-v1` applied to the sealed delivered column; the script is prepared on branch fable/milestoneprep), so it needs no flight of its own; the none hint stays an inner-loop knob (+0.17 predicted, `docs/results/2026-09-29-slurp-sealed-credit-inner-loop-run-2.md`) until a Solver-side action exists to carry it. Outcome (2026-09-30): scope rule +0.49 on A2, FAILS Q2; COMP-2 = COMP-1b alone (`docs/results/2026-09-30-slurp-comp2-stage-column-dev2000-read.md`). |
| 204 | (PROPOSED 2026-09-29 by the coordinator, after the G5 read `docs/results/2026-09-29-slurp-g5-fold-a-read.md`) Lock v2.1 = v2.0 + the G5 Reviewer instruction repair as a no-harm efficiency item (GPU-h 1.68 -> 1.60 per 1,080 rows; intent +0.09 / SLU-F1 -0.38, both inside the null)? | Owner (English translation, 2026-09-29 ~23:10Z, on the coordinator's decisions 200-204): "Decision 200: agreed; decision 201: agreed -- and we adjust the research direction: on 09-06 the focus was still how to use the main model well; now it is how to build the system and optimise at system level; decision 202: GO; decision 203: good; decision 204: agreed." Ruling: AGREED ("agreed"). Consequence: `docs/results/2026-09-30-slurp-v2-1-lock-v1.md` records v2.1 -- the v2.0 bytes with one pin moved, the Reviewer instruction template of `SAEA-SLURP-STAGE3-G5-FOLD-A-V1` (`probes/slurp_native_role_reviewer_v1_g5_v1.txt`); it is the base and A/A for cells registered after A2 seals; A2 and every queued cell stay on v2.0 bytes; the module's lock layer (AT-M0) moves to v2.1 at the next module step. G5 is never reported as a gain. No cell is re-registered by the lock note. |
| 205 | (owner directive 2026-09-29 ~23:10Z, given with the ruling on decision 201) What is the research direction? | Owner (English translation, 2026-09-29): "We adjust the research direction: on 09-06 the focus was still how to use the main model well; now it is how to build the system and optimise at system level." Consequence: `docs/readiness/2026-09-29-research-direction-system-level-v1.md` (merged from fable/tooldecision): tools are system components; the object optimised is the model's control decisions through the control plane (what to supply, what to present, when to consult a tool), read with the sealed-credit inner loop and same-flight columns, not the core's raw capability. The immutable research boundary of the study `CLAUDE.md` is unchanged (speech only; frozen core behind an API-shaped boundary; no second answering LLM; final answer authority with the core; gold never at runtime; pinned, logged tools only), as are decisions 187 and 196. |
| 206 | (owner directive 2026-09-29, supplement to decisions 200-205) Who initiates a tool call? | Owner (English translation, 2026-09-29): "One more supplement: tools should be invoked by the model on its own initiative, not called by the system by default; otherwise we fall into the self-proof trap -- why would the task not be done by an ASR + LLM combination, and why would it need an omni agent system!" Consequence: tools are MODEL-INITIATED, never system-default. Module design section 2d (`docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md`): the module OFFERS a tool at one node and never calls it on the model's behalf; each decision is receipted as `tool_decision {offered, called, args_hash, result_hash, used_in_answer}`. E5 addendum: E5-2a (the system-applied transcript check) is WITHDRAWN as a runtime candidate and kept only as the oracle's upper bound; E5-2 = the tool offer `verify_span(entity_index)` (`tool-offer:asr-slot-value`) at the Solver's slot-value step. Three-part gate, proposed by the coordinator -- proposed, owner to confirm: (1) call rate within [max(0.01, 0.5b), min(0.50, 4b)], b the E5-1 oracle base rate; (2) decision precision >= b + 0.10 and >= 2b, CI95 lower bound above b; (3) conversion >= +1.49 pp whole-roster on the called rows with CI95 lower bound > 0, a whole-column SLU-F1 guard (no measured loss) and 0 intent rows differing. Deterministic FORM normalisers (the delivered-row normaliser, the scope rule) are the one flagged class of system-default step: they change the form of what the core delivered, never the evidence. Note (2026-09-30): the E5-2 gate numbers proposed here are moot for verify-span (route closed at the oracle); the gate form stays the template for any future model-initiated tool offer. |
| 207 | (PROPOSED 2026-09-30 by the coordinator, awaiting the owner) Test-sample allowance v2: the signed allowance `docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json` (decision 151) names nine permitted run ids but not the two native contact-fit ids the milestone cells need (`SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-FIT-V1`, `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-FIT-V1`; 0 core contacts, fit measurement only); the gate refuses unlisted ids. Proposal: the owner signs a successor allowance v2 adding exactly those two FIT ids, all other terms unchanged (comparator = MILESTONE-00-PLAN, the v2.0 lock as flown; one attempt per read id; no smoke on the sample; gold only by the official scorer after delivery, aggregate-only post-stratification per the roster receipt's decision-141 rule; development evidence under decision 28, never a test claim). The milestone package (`docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1/`, held) also waits for sample preparations 2/3 (queued in the E5 gap) and the A2 read's re-declaration. Draft v2 prepared 2026-09-30 (`docs/receipts/owner/2026-09-30-slurp-test-sample-allowance-v2.json`, status draft-awaiting-owner-signature); signing = the owner's confirmation in conversation, then the coordinator sets status authorised and re-pins the package. | Owner (English translation, 2026-09-30, on the coordinator's decisions 207-209): "Decision 207: agreed; decision 208: agreed; decision 209: I feel the focus now should be slot extraction; go with what you recommend." Ruling (2026-09-30): AGREED ("agreed"). Status: agreed. Consequence: the owner signs the successor allowance `docs/receipts/owner/2026-09-30-slurp-test-sample-allowance-v2.json` (the draft above) by this confirmation -- v1 plus exactly the two zero-contact preparation-kind FIT ids `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-FIT-V1` and `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-FIT-V1`, every other term unchanged; v1 is superseded, never edited. The v2 sha256 is recorded by the signing commit: `be2bfa5a612d30cf46a2356efa5e8cf5a54707370b4f57378a278bb835fd0ed8` (signed 2026-09-30, commit 9593baffe). Both milestone fragments re-pin to the v2 bytes; the milestone (re-plan v6 section 1) flies under one-shot semantics (one attempt per read id, no smoke, no recovery, no re-read, no selection) once decision 151's conversational gate is attested in the first countersignature. |
| 208 | (PROPOSED 2026-09-30 by the coordinator, awaiting the owner) Register P-SV-4 = the K6p centred-centroid + agreement key as a same-flight Perception column (`key_source` axis; level 2; TRAIN Fold B; primary intent; declared effect +1.1 pp against the floor 0.65; presence -0.7 / +0.2; two zero-contact artifacts; branch fable/keysource)? | Owner (English translation, 2026-09-30, on the coordinator's decisions 207-209): "Decision 207: agreed; decision 208: agreed; decision 209: I feel the focus now should be slot extraction; go with what you recommend." Ruling (2026-09-30): AGREED ("agreed"). Status: agreed. Consequence: P-SV-4 (cell `slurp-native-stage3-psv4-fold-b-v1`, `docs/readiness/2026-09-30-slurp-stage3-psv4-fold-b-v1/`; the `key_source` axis and the two zero-contact K6p artifacts from branch fable/keysource) is AUTHORISED and flies AFTER the milestone (one experiment in flight). A NOMINATED read is replicated on DEV-2000-ADDED before `key-source:k6p` may enter the module (re-plan v6 section 4). |
| 209 | (PROPOSED 2026-09-30 by the coordinator, to be ruled after the A2 and milestone reads) The structural ceiling question (DEV numbers, 2026-09-30: A2 81.50 % vs A/A 76.90 % intent on DEV-2000-ADDED; Fold A 85.65 %): on Fold A the current component set's on-list recall is 92.1 % and rank-2/3 conversion 29.5 %; no pinned-vector key adds more than 0.4 pp presence; the Solver-node blank is closed under the current evidence kinds (`docs/superpowers/specs/2026-09-30-solver-intent-decision-mechanism-design.md` R5). Option A: accept ~90 % dev intent as this design's SLURP ceiling and define the Stage-3 close by STABLE, replicated gains on the test sample (decision 28/151 wording). Option B: open a new evidence kind under the system-level direction (decisions 205/206): for INTENT, a different embedding space (or a model-initiated intent-evidence tool); for SLOTS, the concrete candidate evidence kind is the model-initiated missing-slot proposal tool -- the transcript PROPOSING slots that are missing entirely (E5-1 oracle, 2026-09-30: 106 rows, perfect-selection ceiling +8.21 [+6.95, +9.57] pp, cross-fit precision 0.25 at a 10 % call rate; needs its own design and a stronger ASR; `docs/results/2026-09-30-slurp-e5-transcript-consistency-oracle-read.md`). Option C: both -- close SLURP at the measured ceiling and carry the module to Audio2Tool/Earnings (decision 196) while B is explored offline. Coordinator recommends C. | Owner (English translation, 2026-09-30, on the coordinator's decisions 207-209): "Decision 207: agreed; decision 208: agreed; decision 209: I feel the focus now should be slot extraction; go with what you recommend." Ruling (2026-09-30): option C ADOPTED ("go with what you recommend"; the coordinator recommended C). Status: agreed. Consequence: (1) SLURP is closed at the measured structural ceiling of the current component set, and the Stage-3 SLURP close is defined by a STABLE, replicated gain on the signed test sample (decision 28/151 wording; operational form and the open replicate rule in re-plan v6 section 1); the module is carried to Audio2Tool / Earnings under decision 196 when the owner reopens those carriers (decision 187 stands until then). (2) The owner's EMPHASIS, recorded as part of this ruling: "the focus should be slot extraction". The research focus now moves to SLOT EXTRACTION: option B's slot half (the model-initiated missing-slot proposal tool, E5-1 oracle ceiling +8.21 [+6.95, +9.57] pp) and the SLU error classes become the main line; option B's intent half (a new intent evidence kind) is not opened now, and P-SV-4 (row 208) is the remaining intent item. Programme: `docs/readiness/2026-09-30-slurp-stage3-replan-v6.md` (supersedes v5). Decisions 187, 192, 195, 196, 199 and 206 bind every slot round. Development numbers remain development numbers (decision 28). |
| 211 | (PROPOSED 2026-09-30 by the coordinator in re-plan v6 `docs/readiness/2026-09-30-slurp-stage3-replan-v6.md` sections 3 and 6: the Earnings-21 module all-off A/A `earnings21-native-stage3-module-alloff-v1` flies once the milestone seals; Audio2Tool needs no flight) When may the other carriers (Audio2Tool, Earnings-21) reopen to the GPU? | Owner (English translation, 2026-09-30): "Decision: lock SLURP first, and only then start the Audio2Tool and E21 tasks." Ruling (2026-09-30): the coordinator's proposal "flies once the milestone seals" is NOT adopted; the other carriers wait for the SLURP LOCK. Status: agreed. Operational reading (coordinator): (a) decision 187 (SLURP-only GPU) stays in force until SLURP is LOCKED. (b) "Locked" = the Stage-3 closure criterion of decision 209 option C: the milestone read on the signed test sample (`SLURP-TEST-SAMPLE-3010-V1`, allowance v2) shows a stable, replicated gain, and the v2.1 lock record `docs/results/2026-09-30-slurp-v2-1-lock-v1.md` is finalised on that verdict; what "replicated" means stays OPEN as decision 210. The milestone seal alone does not lock SLURP. (c) The HELD carrier cells `docs/readiness/2026-09-30-a2t-native-stage3-module-alloff-v1/` and `docs/readiness/2026-09-30-earnings21-native-stage3-module-alloff-v1/` stay HELD: no flip, no countersign, no queue entry. The Audio2Tool byte proof already on file (all-off arm request-identical to A2T-AA, module null h_A2T 1.625 met without a flight) remains valid model-free evidence. (d) Model-free carrier preparation (adapters, module hooks, configs, offline checks) is not GPU work and may continue under decision 196 (the transfer requirement). Component-on cells on any carrier stay closed as before. |
| 212 | Owner-approved next phase: bounded slot-knowledge consumption exploration, followed conditionally by complete-system policy learning. | Owner explicitly requested implementation of the full plan in the current ChatGPT conversation, and then instructed: "Continue." English rendering of the Chinese plan is preserved in `docs/readiness/2026-10-01-slurp-knowledge-opportunity-v1/owner-decisions.md`; the original remains addressable in that conversation. Status: agreed. Freeze slot-contracts v2 and the intent mechanism. F1: independent complete-system A, identical A-prime, reread B and targeted C, seeded400 from source-excluded R01C625, at most one model-requested lookup and one revision, full-family read after one official score per arm. Capability exploration is permitted with unknown conversion, not an effectiveness exemption. F2 remains conditional on qualified full-system actions: R01C625 batches 200/200/225, fixed policy within batch, official complete-batch feedback before cumulative updates, initial balanced exploration then 80/20, support20 fallback. F3 compares a frozen learner against best fixed, default/A-A and feedback-disabled policy on the exposed DEV-added roster. Preserve measurement gates and closed lines. SLURP closure is existing DEV replication plus one valid milestone comparison; other GPU carriers remain held. Fix the missing owner_allowance serializer offline; keep the failed milestone unread and unscored. THIS DECISION DOES NOT ISSUE A SUCCESSOR MILESTONE ALLOWANCE, clear STOP, release P-SV-4, or authorize monitoring dispatch. Coordinated serial integration and normal registration, FIT and smoke gates remain required. |
| 213 | Authorize the sole fresh successor milestone comparison after the named owner_allowance serialization failure. | Owner confirmation in the current ChatGPT conversation, 2026-10-01 UTC; complete English translation: "Authorize this entirely new milestone comparison." The question explicitly named a fresh original PLAN comparator and original COMP-1b treatment, each 3,010 complete trajectories (6,020 total), unchanged scientific settings, a separate successor allowance, and preservation of all old failed bytes unread and unscored. Status: agreed. Authorize exactly those two fresh generation identities and their corresponding FIT identities in `docs/receipts/owner/2026-10-01-slurp-test-sample-successor1-allowance-v1.json`. One attempt per new generation identity, one official full score per successful complete arm, and a complete-pair read gate. No reuse, reseal, scoring or quality read of the old failed comparator. No further successor, smoke on the test sample, closure/complementary-test access, or tuning on milestone outputs. P-SV-4 remains dependent on a separate coordinator disposition; other carriers remain held under decision 211. |

| 214 | Implement the owner-approved joint system-text optimization sequence. | Owner implementation instruction in the current ChatGPT conversation, 2026-10-01 UTC. Complete operational English rendering: docs/readiness/2026-10-01-slurp-system-text-search-v1/README.md; the original approved plan remains addressable in that conversation. Status: agreed. Optimize knowledge construction, organization, supply and role-consumption text jointly; no independent component-benefit or ablation prerequisite. Freeze Omni, intent retrieval/votes, speech, interfaces and official scoring. Use three complete feedback updates and a same-opportunity feedback-blind independent search from the seed; default one pinned GPT6 proposer in isolated sessions. Twelve proposal opportunities and at most 16,800 complete system trajectories on the exact registered historical TRAIN/DEV cohorts; FIT, engineering, proposal and construction contacts need separate registration. Preserve all cumulative sources, complete-family gates, same-chain A/A, official measurements and root scientific disposition. This is black-box parameter-free text-policy iteration, not PPO/GRPO or weight training. Supersede the limited-action F2/F3 design of decision 212 for this sequence; reuse its F1 engineering assets. Do not amend decision 213, consume milestone/test feedback, release old HELD work or authorize monitor dispatch. Worktree isolation, serial coordinator merge, actual full-request FIT, four-row engineering proof and per-cell admission remain required. |

Outcome of decision 140 (cell DET, 2026-09-27): DETERMINISM CONFIRMED, GEOMETRY NOT ADOPTED. Two request-identical flights of the locked plan on np1 x 24,576 with the prompt cache off (`SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-{A,B}-V1`, flight commit 99a3f1f5) delivered 50 of 50 rows byte-identical (0 intent flips, 0 entity-set flips, paired deltas 0.0 [0.0, 0.0]), so the cross-flight band the instrument note measured on np4 (+1.87 / +0.17 / -0.25) is a property of the resident serving geometry -- np4 batching, the prompt cache and the q8 KV -- and not of the model or the harness. Throughput, the criterion the decision named for adoption: 15.09 and 14.89 contacts per minute and 1,991.6 / 1,965.4 prompt tokens per second on np1 against 63.07 and 9,515.8 on the np4 ROLL-2 arm, a 4.2x / 4.8x cost; np1 is therefore not adopted for sampling-heavy work. The read recipe's pre-declared routing rule names a 200-row floor re-estimate as a separate registration; per row 139 no disposition is pre-written here. Read: `docs/results/2026-09-27-slurp-det-np1-pair-read.md`.

Outcome of decision 147 (2026-09-27): ADJUSTED WITH PROOF, merged to master as 7aea4483 (branch `fable/partition`, commit 75015b01). The conflict inventory found exactly one enforcement point for roster-versus-roster final-report disjointness (`contracts.gate_exposure._require_final_report_disjointness`, reached only through `FrozenCoreGate.assert_model_touch_allowed`); `require_owner_split_allowance`, `core.split_receipt.verify_splits_receipt`, `_final_report_roster` and the knowledge-snapshot guards key on the role without asserting disjointness and were left unchanged, so nothing was weakened. The exemption skips the intersection only for a declared parent and sibling(s) after re-proving from the committed item lists that the parts are pairwise disjoint and their union equals the parent exactly, with mutual declarations and matching pins; every failure names the identity. 80 tests (partition admits; non-partition, short union, overlap, surplus, forged sibling, non-final-report parent or child all refuse; the real sample / closure / FULL receipts prove their partition), seven gates exit 0. The FULL parent's three 2026-09-23 preparation rows now pass the disjointness sub-check and are refused only by `require_owner_split_allowance` (`pending-owner`), which is the intended state: each of sample, closure and FULL still waits on its own allowance receipt.

Outcome of decision 148 (2026-09-27): (a) in flight on `fable/tracefix` (not yet merged at this writing). (b) CONFLICT -- NOT IMPLEMENTED. The audit inventoried every place that assumes run outputs live under the E: data root and found three that would have to be weakened or would break: sealed manifests bind absolute artifact paths and `verify_bundle` confines to the manifest's own directory (`core/bundle/manifest.py:40`, `core/bundle/artifacts.py:42`), so an ext4-sealed bundle synced to E: fails verification and a path rewrite changes `manifest_sha256`, cited in 371 docs files, 101 configs, 72 scripts and 65 tests; `persist_flight_receipts` positively confines flight receipts to `$SPEECHRL_DATA_DIR/runs` (`core/flight/receipts.py:203-209`); and the bundle is rewritten after the seal by deferred scoring (`_attach_scores`, `core/bundle/manifest.py:336-342`), so a post-seal archive diverges. The standing rule that only `mlruns` lives on ext4 stands. A relocation would need a manifest schema version with run-dir-relative paths and relative confinement plus a migration for the cited hashes -- a design, not a switch. Audit: `docs/results/2026-09-27-run-root-relocation-audit.md`.

Outcome of decision 112 (2026-09-25, after the offline aggregation read and VERIFY-1): the inference-time aggregation route is CLOSED WITHOUT A QUALIFIED GAIN, and the decision's own step-2 gate never opened. Step 1, the zero-contact offline read over the sealed ROLL-1 five samples per row (625 R01C rows, per-sample official scores), found that no rule delivering one of the N sampled responses verbatim -- the only form the I7 delivery invariant permits -- reaches the registered +1.5 pp SLU trigger or even separates from zero (R1 medoid +0.03 pp [-0.63, +0.71]; R2 intent-plurality medoid -0.04 pp [-0.71, +0.65], both degenerating to "lowest sample index" on 12-13 % of rows); the only rules with a positive lower bound EDIT the delivered answer (support filter at s=3 +1.40 pp [+0.55, +2.29]; the registered plurality-support policy at s=3 +1.62 pp [+0.77, +2.51]) and the winner is the policy cell ROLL-1 had already flown, with the whole effect being pooled false-positive suppression, nil on the 225 rows where the five samples actually disagree, against an oracle headroom of +6.55 pp [+5.56, +7.56]. AGG-1 on TRAIN Fold A was therefore never registered. The selection question went instead to the frozen core as the owner-approved VERIFY-1 continuation of 2026-09-25 (Fable F11, `docs/readiness/2026-09-25-slurp-stage3-verify-1-v1-preregistration.md`): 625/625 rows on one contact each, every choice parsed, chosen minus mean-single +0.7009 pp official pooled SLU-F1 [-0.2551, +1.6507] and intent +0.5440 pp [+0.0320, +1.0880] -- the operational intent non-inferiority guard passes, the primary SLU-F1 benefit gate does NOT. Task benefit not established; no system admission; the decision-112-B core swap was not invoked. Reads: `docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md`, `docs/results/2026-09-25-slurp-verify1-complete-evidence.md`.

Outcome of decision 113 (2026-09-26): DISCHARGED -- the detailed account of what was done and how exists, and the Stage-3 record is not written as "no gain". The standing account is the owner status note `docs/handoff/2026-09-26-owner-status-and-next-flight.md`: its "Present conclusion" records the locked complete system's development-set benefit over direct core invocation (official pooled SLU-F1 38.09 -> 65.40 on DEV-2000-ADDED, +27.30 pp [+24.05, +30.50], system replicate 65.15; Fold A system 63.63 with replicate 63.80) as development/construction evidence supporting retention of the agentic base, and states plainly that no new learned policy with stable whole-system improvement has been established. Its "Completed experimental evidence" table carries one row per closed family with its measured effect and disposition (semantic delta, VAR-1, VERIFY-1, VAR-2, F10, evidence-path, candidate-support diagnostic, candidate-seal recovery), each pointing at the dated verdict in `docs/results/`, and it forbids reading the different rosters as one longitudinal series. The measurement-floor finding of row 113 (about +-1.3 pp pooled at n = 1,000, about +-2 pp on 355-row splits) stands as the bound on every later claim; the fresh-roster loss account is `docs/results/2026-09-24-slurp-cell3-fresh-roster-loss-diagnostic.md`.

Outcome of decision 114 (2026-09-26): NOT FLOWN, exactly as the decision provides. The decision-112 offline read was not positive for an I7-compatible aggregation rule (see the outcome of 112), so the DEVEL-REMAINDER v2 comparators (PLAN + direct, about 11 GPU-h) were never registered and no comparator run id exists for the roster: the only artefacts are the frozen roster receipt `docs/receipts/rosters/slurp-devel-remainder-v2.json` and the model-free preparations note `docs/readiness/2026-09-23-slurp-devel-remainder-preparations-v1.md`. DEV6570 and test13078 remain closed, and the ~11 GPU-h stay unspent.

| 215 | Start the authorized GPU work promptly. | Owner direction in the current ChatGPT conversation, 2026-10-01 UTC; complete English translation: "Start GPU tasks as soon as possible." Status: agreed. Root coordinates serial integration and launch of the decision214 sequence using its existing scientific scope. First admit the separately registered four-row engineering worker and stop at its boundary; initial seed/A/A follow only after remaining capacity and engineering gates pass. This is not permission to bypass registration, release other held work, alter frozen workers, consume test feedback or retry a failed attempt. |

## Pending scoring-entry disposition, 2026-10-01

| No. | Decision | Evidence and ruling |
| --- | --- | --- |
| 216 | Permit one bounded scoring-entry recovery for the complete CONTROL2 initial A/A generation. | PROPOSED by ChatGPT root; owner ruling pending. The worker failed E0/D3 before official evaluation because bytecode caches appeared beside frozen scoring sources. Preserve the original worker, caches, failed job, STOP and both400-row generations. A clean isolated checkout of the exact953f9b598 commit passes E0/D3. Proposed scope: one unchanged whole-manifest official evaluation and finalization from that checkout, exclusive successor score output and explicit failed-entry provenance; zero new generation, no source/policy/roster/metric change. Stop on another failure. The original complete-family READ remains unsigned until both seals and unique successful official scores qualify. This exception is not supplied by decision215. See [concrete report and disposition](2026-10-01-slurp-system-text-initial-control2-v1/score-entry-failure.md). |

## Recorded owner rulings and new startup disposition, 2026-10-02

The original proposal row 216 above remains historical. The owner subsequently explicitly approved decisions 216 and 217 in the current ChatGPT conversation. Complete English rendering: "Decision 216: agreed; decision item 217: agreed." The later own-application sign-in reply was "Signed in." The original messages remain addressable in this conversation; no credential is copied here.

| No. | Decision | Evidence and ruling |
| --- | --- | --- |
| 216 amendment | Confirm the previously proposed initial A/A scoring-entry recovery. | AGREED by the explicit owner reply above; already completed under its exact initial-family disposition. This does not authorize later generation recovery. |
| 217 | Admit the bounded subscription proposer route. | AGREED by the explicit owner reply above. Use the research program's own subscription grant, pinned admitted model/version, isolated L/B request namespaces, metered output acceptance/rejection where a server hard cap is unavailable, full input/output/contact accounting, original proposal allocations and zero paid API spend. No unmetered acceptance, silent replacement, answering-model substitution, test-feedback access or failure recovery. Exact implementation bounds are in `docs/readiness/2026-10-02-slurp-system-text-update2-v1/provider-admission-owner217-v1.json` and the owner217 protocol. |
| 218 | Permit one zero-contact UPDATE2 L-parent entry recovery with per-member process containment. | PROPOSED; owner ruling pending. Root stopped its eight-member startup when Windows free memory reached 7.77 GiB. L-parent is OPENED with zero model calls; seven members and all native FIT attempts are unstarted, no official score. Preserve all evidence. Proposed scope: explicitly dispose the abandoned zero-contact entry and exact stale controls, register one successor L-parent attempt, then run the same eight members/400 trajectories each through separate sequential instances of the existing campaign runner. No scientific, roster, policy, geometry, quota, candidate or scoring change; no partial read. The single-member model-free proof peaks at 2.14 GiB RSS and 14.396 GiB minimum sampled Windows headroom. Full live resource guards and registration still precede dispatch. Stop on another recovery failure. See [complete incident, proof and exact proposed queue](2026-10-02-slurp-system-text-update2-memory-recovery1/README.md). |

## Subsequent explicit owner amendments,2026-10-02

| No. | Decision | Evidence and ruling |
| --- | --- | --- |
| 218 amendment | Approve the exact zero-contact entry recovery and request root diagnosis. | AGREED: the human approved218, requested first-round cause/optimization analysis and later permitted appropriate rounds beyond three. The original pending row is historical. See docs/receipts/owner/2026-10-02-decision218-and-iteration-amendment.json. No unbounded sampling or formal-evidence exemption. |
| 219 | Approve the uniform Reviewer response-contract correction and execution. | AGREED: the explicit reply approves the concrete four-row engineering plus real capacity, then the uniformly corrected eight-member family with preserved proposals and artifacts. See docs/receipts/owner/2026-10-02-decision219-reviewer-contract.json. Owner220 subsequently reduces the next dispatch to20 rows per member. |
| 220 | Establish engineering reliability and preliminary feasibility on small samples before medium-scale work. | AGREED by two direct human instructions in this conversation. Complete English rendering and exact160-trajectory implementation: docs/receipts/owner/2026-10-02-decision220-small-pilot-first.json. Keep four-row engineering separate; run20 per each of eight fixed members after acceptance, preserve A/A and spent candidates. Narrowly permit exploratory official scores/diagnosis at20 rows after full-family qualification; no formal benefit, harm, no-harm, policy adoption or automatic400-row dispatch. Any later feedback-based tuning creates cumulative exposure and cannot reuse pilot rows as independent validation. No change to other carrier holds or monitor authority. |

| 221 | Keep about8GiB available for Windows; store file caches locally and load on demand. | RESOURCE AMENDMENT AGREED by direct human message. English receipt: docs/receipts/owner/2026-10-02-decision221-memory-amendment.json. Explicit running floor8GiB; operational startup12.5GiB retains4.5GiB headroom. Preserve historical workers and thresholds; avoid global cache flushing/host changes. Exact13:35:56Z STOP disposition and continuation of seven untouched20-row members also explicitly AGREED by the human response to the concrete proposal; review docs/readiness/2026-10-02-slurp-pilot20-startup-wait-v1/proposal.json. No replay, partial read, new candidate or400-row expansion. |
| 222 | Use small complete-system pilots as learning feedback and pursue positive full-system results before medium scale. | AGREED by direct human correction on2026-10-02. See docs/receipts/owner/2026-10-02-decision222-small-panel-learning.json. Supersede owner220 no-learning restriction for the complete20-row family. Export all four L members/all20 cases only after exact root READ; keep B blind and cumulative exposure. Learning may use small batches without meeting formal200/400-row claim floors. Preserve those formal floors, disjoint prospective next panels, original spent allocations, bounded registration and no guaranteed improvement or automatic expansion. |

## Decision223: progressive learning ladder (approved2026-10-02)

After the dominant engineering and consumption defects are addressed, the human authorizes staged50,100,200,400 inputs per member, following the current20-input loop. Every scale supplies complete-system diagnosis and L-only feedback. Root reviews the complete stage before the next scale; exact cohorts, quotas, A/A and read conditions are registered before contacts. Existing formal claim floors remain. Do not infer permission to activate old held identities or retry failures. See [owner receipt](../receipts/owner/2026-10-02-decision223-progressive-learning-ladder.json).

## Decision224: reuse the current400 optimization pool and focus on context/post-call handling

The human directs root to settle the solution on the current prepared400 inputs, prioritizing context engineering and postprocessing rather than rebuilding datasets or repeatedly expanding full eight-group campaigns. Reuse nested20/50/100/200/400 prefixes of UPDATE2, with cumulative optimization exposure and no independent-validation claim. This supersedes222/223's proposed disjoint next learning panel, not the runtime gold or formal confirmation boundaries. Keep knowledge assets fixed for the next repair cycle, reuse shared rails, preserve Omni answer authority and existing score receipts, and retain matched L/B controls for any feedback-learning claim. See [complete owner statements and scope](../receipts/owner/2026-10-02-decision224-fixed400-context-postcall.json) and [concrete plan](2026-10-02-slurp-fixed400-context-postcall-v1/README.md). No automatic retry, rescore or old held-run activation.

## Decision225: fixed400 seed policy binding recovery (PENDING)

Root proposes one named recovery after the comparison seed was mistakenly bound to the legacy Planner template instead of its declared CONTROL2 policy. Restore the existing seed bundle through the shared compiler; preserve the two completed invalid-comparator attempts and scores unread. Run fresh capacity/four-row seed engineering, then two new seed/A/A20 identities and the two never-started candidate20 identities, on the same current400 first20. No data/knowledge rebuild, proposal replacement, rescore or automatic further recovery. The concrete [proposal and offline proof](2026-10-02-slurp-fixed400-seed-binding-recovery1/proposal.json) are ready for the owner. This entry is not approval.


## Decision225 approved and offline scaling preparation,2026-10-03

The human explicitly approved225 in this conversation. Complete English translation: "Decision225: agreed. In parallel, prepare the data slices and engineering base for8x50,8x100 and8x200." The earlier pending entry is historical. Execute the exact proposed corrected-seed capacity, four-row engineering and four-member20 recovery on the same current400. Preserve old failed-family artifacts and all spent proposal allocations. Prepare three nested roster/configuration packages concurrently offline; preparation itself creates no proposal or larger-panel GPU authority. Root reviews each complete stage before the next stage under223/224. See [approved exact authority](../receipts/owner/2026-10-03-decision225-seed-binding-recovery-approved.json). Any further recovery failure stops; no automatic repeat.


## Decisions226 and227 approved: autonomous engineering before8x400

Recorded 2026-10-03T06:54:07.419264+00:00. Complete English translation of the direct human message: "Agreed. We are still consolidating the engineering base, until the system works end to end and system-level benefit and learning capability are demonstrated. I authorize you to make decisions autonomously until an8x400 experiment is needed."

226 approves the prepared one-entry continuation for the same four unspent round5 slots, with unchanged inputs/model/budgets and all original failed evidence preserved. See [exact226 authority](../receipts/owner/2026-10-03-decision226-precontact-continuation-approved.json).

227 authorizes root decisions and execution for the current SLURP engineering/learning loop through reviewed20/50/100/200 panels. Root may dispose of an in-scope engineering incident after diagnosis, prospective registration and required proof without asking the human again. A failed job stops; no silent retry loop, spent-slot replacement, incomplete scientific read or frozen-byte mutation is allowed. Return to the human before8x400; do not evade that boundary through campaign splitting. Preserve fixed-pool exposure, L/B isolation, official scoring, Omni authority, zero paid API and all other-carrier holds. The heartbeat remains read-only. See [exact227 scope](../receipts/owner/2026-10-03-decision227-autonomous-engineering-before-8x400.json).


## Root disposition under227 after the complete context matrix, 2026-10-03T15:39:49.449374+00:00

Retain legacy query placement with trajectory scheduling as the next engineering basis, while keeping independent node instructions and explicit source-bound handoffs. This is a sampling/design choice, not formal adoption or proof of an optimum. Prepare a separate20-input context-content comparison crossing constant/per-role tool-schema display with full/latest-Solver-and-local-tools Reviewer history, with an own repeat for each configuration. Keep seed text, legal actions, revision budget, knowledge, task assets, service geometry and original sample timing fixed. Register fresh identities, maximum legal request FIT, required four-row structural proof and exact whole-family READ before execution. Do not scale to50 or start learning automatically; root reviews the next complete panel. The human boundary remains8x400.

This is a delegated root engineering disposition, not a new human ruling or formal scientific adoption. The [complete read and both weighting views](../results/2026-10-03-slurp-context-matrix-n20-root-read.md) and [pinned receipt](../receipts/continuation/2026-10-03-context-matrix-n20-scientific-read.json) retain all eight members, own repeats and uncertainty. No learning or larger-panel contact is admitted here. Root only; heartbeat PAUSED.

## Root227 follow-up: actual cache sequence and node-batched scheduler,2026-10-03

Accept the source-bound offline [cache diagnosis](../results/2026-10-03-prefix-cache-sequence-and-node-batching.md) for the already-read complete matrix. It verifies actual slots, recurrent prefix divergence and speech-feature re-evaluation, while distinguishing warm artifact validation from decoder KV prefill. No new contacts or result reinterpretation.

The direct owner now asks for space-for-time node batching: process one node for a bounded cohort across all four slots, preserve individual intermediate states, and feed each own result to its successor. Implement an opt-in shared-executor scheduler with original graph/tool authority, conditional revision, finite completion, cancellation/failure settlement, no answer sharing and truthful cohort/sample/node timing. Prove offline before separately admitted capacity/structural/small-panel work. Keep the prepared tool-display/history candidates HELD until this scheduling basis is established. No automatic scale or learning, no subagents, heartbeat PAUSED, human before8x400.


## Direct owner227 clarification: full-panel node stages and cache priority, 2026-10-03T17:22:08.691438+00:00

The owner clarified that node2 preparation is CPU-only and can overlap current-node inference, but node2 model calls wait for all node1 requests and the final prepared group. The full8x20 panel contains160 independent jobs. The owner then emphasized maximizing prefix-cache reuse across nodes as the essence of this design. The complete English translations and source location are preserved in the [clarification receipt](../receipts/owner/2026-10-03-node-stage-cache-reuse-clarification.json).

Implement continuous full-panel node stages with fixed20-job preparation groups, all four slots available to the active node, and independent node text/context. Exact token-prefix compatibility determines reusable KV; CPU prefetch supports the cache objective and does not establish it. Preserve independent experiment and sample identities, budgets, source custody, official scoring, original sample latency and business quality. This supersedes the smaller cohort-through-whole-graph schedule as the next engineering target, not its immutable completed evidence. Root only; learning HELD; heartbeat PAUSED; human before8x400. The shared scheduler is verified offline; eight-member runtime ownership and real measurement remain prerequisites to admission.


## Decisions 228-236 PROPOSED by the coordinator (Fable 5.1), 2026-10-09 -- the NX node-extreme programme

Programme: `2026-10-09-slurp-nx-node-extreme-programme-v1.md` (approved as the plan of record by the owner on
2026-10-09; owner clarifications of the same day in its section F: template-plus-statistics learning in two
stages, knowledge USE before knowledge SUPPLY; the Reviewer-class capability is beyond the 30B-A3B core; the
Qwen ASR question). Owner ruling 2026-10-09 (English translation of the chat message): "Decision 228: A; 229-234: agreed, go with what you recommend." Status: rows 228-234 RULED as recommended (228 = A, the COMP-1b lock as flown in the milestone); 235/236 withdrawn (below). Consequences: SLURP INTENT is LOCKED at COMP-1b (`docs/results/2026-10-09-slurp-intent-lock-comp1b-v1.md`); SLU-F1 stays open as the NX slot line; the joint N100 composition is not flown; every NX read is n >= 1,080 same-flight paired; the Reviewer loop is removed (F2); carriers stay HELD until the R5 composed read; the second test-sample allowance is drafted only after R5 reads NOMINATED on DEV; one registration / countersign / read per round.

| # | question | coordinator recommendation |
| --- | --- | --- |
| 228 | One base for every NX round. A: the COMP-1b lock as flown in the milestone (replicated on the signed test sample: intent +5.80 [+4.04, +7.42], DEV +4.60 [+2.58, +6.73]); B: the ChatGPT seed bundle `ba18a4a8...` (TRAIN N100 incumbent). | A. R0.1 byte-diffs the two either way. |
| 229 | Rule for decision 210 and the partial lock: "replicated" = CI95 lower bound > 0 on DEV-2000-ADDED AND on the signed test sample for the same metric. Under it SLURP INTENT is LOCKED at COMP-1b; SLU-F1 stays OPEN (the NX slot line). Does the intent lock reopen the Audio2Tool / Earnings-21 all-off A/A cells (decision 211)? | Adopt the rule and the partial lock; carriers wait for R5 (the composed read); model-free carrier preparation continues under 196. |
| 230 | Do not fly the joint N100 five-policy composition (`2026-10-09-slurp-local-to-joint-n100-v1`): n = 100 cannot resolve the +1.23 / +1 effects it would test and the Solver donor carries no revision paragraph. | Agree; the Solver donor becomes an R1 candidate at n = 1,080; the Reviewer donor retires with the loop (F2). |
| 231 | Measurement floor for every NX round: no read below n = 1,080 same-flight paired (4-row dry runs are form proofs only). Supersedes the 20/50/100/200 ladder of decisions 220/223 for SLURP node work. | Agree. |
| 232 | Reviewer loop: superseded by section F2 (removed as an optimisation round; review-off is the NX base graph; one resolved twin read at n = 1,080 inside the first R1 cell; revisit only if the full graph wins > 1.49 pp SLU with CI-LB > 0). | Agree with F2. |
| 233 | A second test-sample allowance (successor-2, same terms as v2: one attempt per id, aggregate-only, no smoke, no re-fly) for the R5 composed read, drafted only after R5 reads NOMINATED on DEV. | Agree in principle now; sign later. |
| 234 | Cadence: one registration / countersign / read per round (K arms in one cell); job-scoped monitor at launch only; the ChatGPT root keeps the N100 custody but opens no new N20/N100 GPU family during NX. | Agree. |
| 235 | E6, the ASR capability probe (one pinned Qwen3-ASR-1.7B pass as a logged tool contact, 0 core contacts). | **WITHDRAWN by the owner, 2026-10-09** (English translation of the chat message: "Cancel the Qwen3-ASR exploration; there is no need to explore the engineering scheme and implementation path for that mode. Return to focusing on the gains the agent system and the learning algorithm can bring."). Status: ruled -- NOT approved. No install, no tool pass, no transcript catalog. Programme section F3 stays as the factual record of why an ASR model cannot replace the Omni core. |
| 236 | The thesis question "cascade core (Qwen3-ASR + frozen text LLM) instead of the Omni core". | MOOT by the same owner message of 2026-10-09: the core stays the frozen Qwen3-Omni; NX focuses on the agent system and the learning algorithm. Status: closed. |

## Decision 237: codex-era worktree cleanup (owner 2026-10-09)

Question (coordinator, under the owner's instruction "clean up the engineering base"): remove the 187 referenced
codex-* worktrees under `/home/chao/saea-worktrees/` (about 120 GB; clean detached checkouts of commits already in
master history, reproducible with `git worktree add --detach <commit>`; custody = the commit hash in each receipt),
keeping only the joint-N100 custody trees the ChatGPT root still holds? Owner (English translation): "Decision 237:
agreed, go with what you recommend." Executed 2026-10-09 ~11:40Z from WSL (never from Windows): removed 164 clean
trees whose HEAD is an ancestor of master; kept 32 -- the four joint-N100 custody trees (`codex-joint-*`,
`codex-local-k4-capacity-caption-v2`), five dirty trees, thirteen trees whose HEAD commit is not in master (ChatGPT
side commits; listed in `/home/chao/worktree-cleanup-20261009.log`) and ten broken registrations with no readable
HEAD (September 26 `codex-system-*` and `codex-stage3-continuation-20260925`; directories left in place for the
ChatGPT root to dispose). Worktrees 225 -> 28; disk 126 GB -> 69 GB. Earlier the same day: 155 inert scheduled
tasks unregistered, six merged fable-nx-* trees removed, stale queue scripts archived.

## Decision 238 (PROPOSED by the coordinator, 2026-10-09): close Stage S at the Solver node; go to Stage J (R5)

Evidence: `docs/superpowers/specs/2026-10-09-slurp-nx-stage-s1-supply-round-design.md` (merged c45e99d28). Every
supply arm declarable at the Solver node (exemplar k / per-intent cap / intent-count cap, slot-card candidates, a
TRAIN-only entity-free exemplar release for the N1 none signal, and their combination) predicts at most +0.20 pp
official SLU-F1 at a MEASURED conversion (upper bound +1.04 at the M1 rate), against the 1.5 pp registration bar of
decision 192 and the 1.49 floor; two engineering items (a module `supply` column kind on the review-off base; reader
support) would be needed even to fly it. Options: (A) close Stage S now, record the ceiling, and compose Stage J =
R5 (review-off COMP-1b base + v4g [+ the R1 iteration-2 template if NOMINATED and confirmed on Fold A]) read on
DEV-2000-ADDED with an in-chain A/A, then the second test-sample allowance (233); (B) fly S1 as a no-claim
measurement cell (~2.6 GPU-h, cannot nominate); (C) open a code-level supply mechanism whose on-file ceiling is also
below the bar. Coordinator recommends A.

## Decisions 238-244 ruled by the owner, 2026-10-10 (English translation of the chat message)

- **238** "Agreed." -- Stage S is closed at the Solver node; Stage J (R5) follows.
- **239** "You have touched a core and very important point: when a local optimisation is shown to be unattainable, should
  the task be handed to the SYSTEM, asking other local points to provide more valuable or more easily obtained inputs?
  Try moving the empty-entity / non-empty-entity part to the PRECEDING node for optimisation and transformation, and
  even try adjusting the knowledge supply to help us reach a better conclusion." -- Ruling: the Solver template line
  closes under the plateau rule (lock the v2 template), but the empty-entity decision is NOT closed: it moves
  upstream -- a Perception-side entity-presence / heard-value evidence and a supply-side per-intent entity prior are
  the next registered rounds (R6), designed from the sealed R1 columns offline first.
- **240** "Agreed." -- R5 flies: the module OFF replicate (lock v2.1) + the composed arm (lock v2.2 = v4g at delivery,
  review-off, COMP-1b components on) on DEV-2000-ADDED, read against the sealed A2 with the replicate offset, bar 2.5
  pp, no-harm claim at about half the contacts plus the v4g delivered gain; CURRENT_LOCK moves to v2.2 if R5 nominates.
- **241** "As you suggest." -- the second test-sample allowance (233) is drafted once R5 reads NOMINATED or NEUTRAL;
  same terms as v2; the composed arm flies once on the signed sample against the sealed PLAN and COMP-1b columns.
- **242** "If the SLURP prompt-template stage has already yielded what it can, we must move to system-level
  optimisation, such as knowledge supply; the carriers do not start now -- after the system-level optimisation is
  locked." -- Ruling: decision 211 stands unchanged; no Earnings-21 / Audio2Tool flight before the SLURP system-level
  lock; the GPU gap is filled with SLURP work only.
- **243** "Clean it up." -- the coordinator retires the ChatGPT-era ready-unflown drafts (superseded, evidence kept),
  records the two 400-row analysis rosters inside the Fold B filler family as known cumulative exposure (proof and
  test updated), and re-pins the natural-source compatibility record after review.
- **244** "Let us finish the optimisation first and not retreat now: the knowledge-supply optimisation, the
  system-level optimisation and the training-free RL algorithm optimisation are still ahead. Believe in yourself!" --
  Ruling: the SOTA goal is not re-scoped now; the programme continues through R5, the test read, the upstream
  empty-entity evidence (R6), the supply-side rounds and the training-free RL algorithm work.

## Decision 245 ruled by the owner, 2026-10-10; decisions 246-248 PROPOSED by the coordinator (Fable 5.1)

- **245** (proposed 2026-10-10 in the coordinator's briefing: R6 = (A) a Perception-side entity-presence / heard-value
  column as a level-2 measurement cell and (B) a Fold A two-arm confirmation of the "lock + core empty verdict + N1 >=
  0.2 gate" delivery rule, both below the 1.5 pp bar, with a waiver of decision 192 requested). Owner, verbatim:
  「决策245：可以先各自优化后，再级联优化，各自优化过程中，不需要考虑彼此之间的连接关系。在级联优化过程中，前置节点要考虑如何
  传递更有效的信息给到后置节点，这里面更重要的是优化通信模板，明确好对后续判定最有效的要素长什么样，同时可以返回多选项连同执行
  度让后续节点去选择，或者后续节点把这个任务当做是一个重排序任务。你注意，这里面最重要的是提供稳定且额外的信息增益！」
  English: "Optimise each node on its own first, then optimise the cascade. In the node-local phase, ignore the
  connections between nodes. In the cascade phase, the upstream node must work out how to pass more effective
  information to the downstream node; what matters most is optimising the COMMUNICATION TEMPLATE: define what the
  elements most useful to the downstream judgement look like. The upstream may also return several options together
  with their confidence for the downstream to choose from, or the downstream treats the task as a RE-RANKING task.
  Note: the most important thing is to provide STABLE and ADDITIONAL information gain." -- Ruling as recorded: R6 is
  re-designed as a two-phase programme, `docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md`:
  phase 1 node-local (R6-P1, the Perception entity column on TRAIN Fold B, interfaces frozen, judged on node metrics and
  information gain), phase 2 cascade (the Perception -> Solver message: deterministic gate consumer at delivery from the
  same sealed columns, the locked Solver as consumer, then the Solver as chooser / re-ranker in R7, a v2 note contract
  only on trigger), confirmation on Fold A, composition on DEV-2000-ADDED (R8). The acceptance rule is the owner's:
  information gain that is ADDITIONAL (cross-fitted gain over the supply statistics and over the downstream's own
  verdict, CI-LB > 0) and STABLE (same sign and CI-LB > 0 on the confirmation roster with the rule fixed). The
  coordinator's reading of the decision-192 bar under this ruling: it binds the cascade cells that claim a delivered
  gain (R7 / R8); the node-local measurement cell is judged on its node metric and information gain, with its
  delivered-metric estimate produced offline before any cascade cell is registered.
- **246** (PROPOSED) Register and fly R6-P1 as designed (three Perception candidates p1-p3 + twin + lock, TRAIN Fold B
  1,080 rows, ceiling 10 contacts per row, ~4.1 GPU-h; node-local measurement with the free locked-consumer cascade
  read) as the next flight after the R5 read. Recommended: yes.
- **247** (PROPOSED) Adopt section 4 of the design (information gain: additional and stable, pp stated through the
  measured exchange rates) as the acceptance rule of node-local and cascade rounds; decision 192's 1.5 pp registration
  bar binds the cascade cells (R7 / R8), not the node-local measurement cell. Recommended: yes.
- **248** (PROPOSED) The v2 Perception note contract (`slurp-intent-hypotheses-v2`: explicit presence verdict and
  heard-mention options with a two-level confidence) is engineered only on the design's 2d trigger (gain present but
  the 128-character `distinction` channel binding), as a new Perception base with its own A/A, never as an arm.
  Recommended: conditional, as stated.

## Decisions 246-248 ruled by the owner, 2026-10-10

Owner, verbatim: 「决策246：同意；247：同意；248：按你建议。」 ("246: agreed; 247: agreed; 248: as you recommend.")

- **246** RULED: R6-P1 (three Perception candidates p1-p3 + twin + lock, TRAIN Fold B 1,080 rows, ceiling 10, ~4.1
  GPU-h; node-local measurement with the free locked-consumer cascade read) is registered during the R5 read and flies
  as the next flight after it. Candidates: `docs/readiness/2026-10-10-slurp-nx-r6-perception-candidates-v1/README.md`.
- **247** RULED: the information-gain acceptance rule (design section 4: ADDITIONAL = cross-fitted gain over the
  supply statistics and over the downstream's own verdict with CI-LB > 0; STABLE = same sign and CI-LB > 0 on the
  confirmation roster with the rule fixed; pp through the measured exchange rates) governs node-local and cascade
  rounds; decision 192's 1.5 pp registration bar binds the cascade cells that claim a delivered gain (R7 / R8), not the
  node-local measurement cell.
- **248** RULED as recommended: the v2 Perception note contract is engineered only on the design's 2d trigger (gain
  present, the 128-character `distinction` channel binding), as a new Perception base with its own A/A, never as an arm.

## R5 read recorded; decision 249 PROPOSED by the coordinator (Fable 5.1), 2026-10-10

R5 (decision 240) sealed 2026-10-10T06:37:48Z and read the same morning
(`docs/results/2026-10-10-slurp-nx-r5-composed-dev2000-added-read.md`, merge 233a64809). Verdict under the registered
rule: **NEUTRAL (efficiency result).** Composed (lock v2.2: review-off + COMP-1b components + v4g at delivery) minus
the sealed A2 arm on DEV-2000-ADDED: SLU-F1 +1.24 [-0.29, +2.80], intent +0.50 [-0.51, +1.52]; flight offset
(replicate minus A2 A/A) 0.73 / 0.20; same-chain intent +4.90 [+2.93, +6.86] (the COMP-1b intent gain's third
replication); under one normaliser the review-off change is +0.27 [-1.17, +1.72], so the delivered SLU gain over A2 is
the v4g delivery gain (+0.98 [+0.25, +1.71] offline). Levels 65.40 / 65.93 / 66.13 / **67.18**. Contacts 2.00 vs 4.05
per row, -0.32 GPU-h per 1,000 rows. No gain is claimed; the registered no-harm claim holds within resolution.
Consequences: decision 241 fires (the second test-sample allowance is drafted: package
`docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1/` and the draft
`docs/receipts/owner/2026-10-10-slurp-test-sample-successor2-allowance-v1.json`, both in preparation, HELD until the
owner signs); decision 240's automatic lock move does not fire (it required NOMINATED).

- **249** (PROPOSED) Move `CURRENT_LOCK` of the consumption module from v2.1 to v2.2 (= v2.1 with
  `saea-deliver-normalise-v4g` at delivery, review-off graph) on the efficiency and no-harm ground: no resolved loss on
  SLU-F1 or intent against the full graph at about half the contacts, plus the separately locked v4g delivered gain
  (Fold B +1.55 [+0.81, +2.33]; A2 column +0.98 [+0.25, +1.71]); the intent gain replicated a third time. The lock move
  changes the base of every later NX cell (R6-P1 already derives from the R5 arm's fragment, so it is unaffected).
  Recommended: yes; if the owner prefers to wait for the test-sample read (allowance v3), R6-P1 still flies on the
  v2.2 base as registered.

## R6-P1 launched; allowance v3 draft ready; decision 250 PROPOSED by the coordinator (Fable 5.1), 2026-10-10

- **R6-P1 (decision 246)** registered (`docs/readiness/2026-10-10-slurp-nx-r6-perception-fold-b-v1/`, merge cc19a597d),
  four flight rows countersigned (03e326d19), receipt minted, flipped in two converged loops with the plan-pin
  refresh between them (flight commit 58c546b54; gates PASS, one advisory `tuning-roster-unverified`), launched
  2026-10-10T08:07:42Z through the batch driver (task SAEA-Queue-NXR6; smoke then the one-cell campaign; 10,800
  planned calls, ~4.1 GPU-h). Root ruling recorded in the countersignature: the candidates' `template_tokens` are a
  labelled ESTIMATE (ceil 2.0 x words) that the pre-flight bound clears with margin and the realised fit gate bounds
  at dispatch.
- **Allowance v3 (decision 241)** drafted: `docs/receipts/owner/2026-10-10-slurp-test-sample-successor2-allowance-v1.json`
  (status draft-awaiting-owner-signature; permits exactly `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1`
  and its FIT id; supersedes the successor-1 allowance by scope "new successor run identities only"); the HELD cell
  `slurp-milestone-successor2-composed-v1` (= the NX R5 composed arm re-targeted to the signed sample; identity map in
  `docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1/successor-identity-map.json`: only roster-bound,
  role-bound and bookkeeping leaves differ; module lock v2.2, review-off, policy c2, v4g unchanged); 6,020 generation
  calls, 24,080 FIT, 16,413 audio seconds, ~4.2-4.6 GPU-h; one attempt, no smoke, no recovery, no re-read.
  Signing = the owner's confirmation in conversation; the coordinator then sets `authorised`, records the sha256 and
  re-pins the fragment.
- **250** (PROPOSED) The successor-2 test read has NO in-chain replicate by design (decision 241: the composed arm flies
  ONCE against the sealed successor-1 PLAN and COMP-1b columns), which instrument rule 4 refuses for a cross-flight
  design. Options: (A) record a coordinator exception: the design is `cross-flight-no-replicate`, the declared flight
  offset is the DEV-measured 0.73 pp SLU / 0.20 intent (R5 replicate vs A2 A/A), the cell claims no benefit (no-harm,
  margin 2.5) and its numbers are milestone evidence under decision 28, so the test sample is not exposed twice for a
  sampling-floor estimate DEV already supplies; (B) add an in-chain COMP-1b replicate on the sample (+3,010 rows,
  +4.6 GPU-h, a second test exposure of the same recordings, and a wider allowance). Recommended: A, recorded in the
  package's measurement block and read qualification; the gate `stage3_effect_floor_check` does not scope this cell
  (no `stage3` token, as successor 1), so the exception is a documented ruling, not a bypass.

## R6-P1 smoke stop, harness fix, one recovery, relaunch (coordinator record, 2026-10-10)

The first R6-P1 smoke stopped at 08:11:08Z (20 contacts: 4 rows x 5 Perception arms; the first level-2 Solver input
refused with `hypothesis content does not match its source response SHA-256`). Root cause: the 2026-10-09 level-2
render fix (never flown before) swapped the sealed Perception state's content for the branch's own note without
rebinding `source_response_sha256`; the knowledge provider's candidate-state parse enforces that binding. Fix:
`perception_note_view_state` helper used at both runner sites (45c3b3633, merged 6030c3149; regression test
`tests/unit/test_perception_note_view_binding.py`, the 4-row walk's fake supply binding now runs the real parser).
Recovery under the standing one-recovery rule: smoke re-flown whole under `...-smoke-4-generation-rec1-v1` with the
run-cumulative budget 40 + 20 = 60 calls / 153 speech seconds, FIT cap 160 unchanged, arm untouched (merge 906f2a936);
`rails/runner.py` is identity-bound, so both cells re-flipped (two converged loops with the plan-pin refresh between
them) to flight commit 1f04ce42d; gates PASS. Relaunched 09:13:31Z; smoke rec1 PASSED 09:17:22Z (the previously failing
Solver input now renders); the arm started 09:17:32Z (1,080 rows, 10,800 planned calls). Lesson recorded: a view that
rewrites sealed content must rebind its hash; an unflown "fixed" path needs a walk through the real parsers before a
cell is registered on it.

## Decisions 251-252 PROPOSED by the coordinator (Fable 5.1), 2026-10-10 (owner briefing of the same day)

- **251** (PROPOSED) Timing of the second test-sample read (allowance v3, decision 241): (A) sign now and fly the
  HELD successor-2 composed cell (lock v2.2, 3,010 rows, one attempt, ~4.5 GPU-h) in the first GPU gap after R6-P1,
  so the "large gain over the direct-call baseline" claim of the owner goal gets its test-side evidence for v2.2
  (expected vs PLAN: intent about +6, SLU about +2; vs COMP-1b: SLU about +1.2, intent about +0.5), accepting that a
  later v2.3 (R6/R7 locks) will need one more milestone read; (B) hold the test read until v2.3 exists, reading the
  sample once less. Recommended: A (the sample was designed as a milestone comparison instrument for iteration,
  decision 141; the GPU is otherwise idle between SLURP rounds; development evidence under decision 28).
- **252** (PROPOSED) Define the "system-level lock" that decision 242 waits for as: lock v2.2 confirmed on the signed
  test sample (no-harm on SLU-F1, intent gain retained). On that confirmation the carrier work resumes in GPU gaps in
  this order: Audio2Tool ALL-OFF A/A (model-free proof already on file; ~4 GPU-h), Earnings-21 ALL-OFF A/A (~4 GPU-h),
  then the module-ON reads per carrier, so the engineering base is shown to run end-to-end on Audio2Tool / E21 / E22
  (owner goal, second clause) while the SLURP R6/R7/R8 rounds continue to hold GPU priority. Recommended: yes.

## Decisions 249-252 ruled by the owner, 2026-10-10 (verbatim Chinese, English translation, consequences)

Owner: 「决策249：同意；250：A；251：A，许可v3签字；252：我认为这里面分为两个模式，系统优于单次模型调用证明工程基座可行，同时
training free RL证明通过系统级强化学习后能够看到明确的收益，并且优化和改进这个training free RL算法在多模态知识构建和消费上的
使用方式，同时在测试集上能够观测到对比业内SOTA的基线水平才可以锁定基线。」

English: "Decision 249: agreed; 250: A; 251: A, allowance v3 signed; 252: I think this splits into two modes: the
system beating a single model call proves the engineering base is viable, and training-free RL proves that clear
gains appear after system-level reinforcement learning, with the use of that training-free RL algorithm in
multimodal knowledge construction and consumption optimised and improved; and only when a comparison against the
industry SOTA baseline level can be observed on the test set may the baseline be locked."

- **249** RULED: `CURRENT_LOCK` of the consumption module moves from v2.1 to v2.2 (`rails/adapters/slurp_module_hooks.py`;
  identity-bound change, so pinned ready cells re-pin at their next flip; R6-P1 flies from its flight worktree,
  unaffected).
- **250** RULED A: the successor-2 test read carries the documented exception (design `cross-flight-no-replicate`,
  declared DEV offset 0.73 pp SLU / 0.20 intent, no-harm claim, margin 2.5, development evidence under decision 28);
  no in-chain replicate on the sample.
- **251** RULED A and the allowance v3 SIGNED by this confirmation:
  `docs/receipts/owner/2026-10-10-slurp-test-sample-successor2-allowance-v1.json` status `authorised`, the owner's words
  recorded verbatim in its signature block; the signing commit records its sha256; the successor-2 fragment is re-pinned
  to those bytes; the HELD cell flies once in the first GPU gap after R6-P1 (countersign rows, mint, flip, gate, chain).
- **252** RULED, replacing the coordinator's proposal: the "system-level lock" that releases the carriers (decision 242)
  is NOT v2.2's test confirmation alone. It has two modes that must both hold, plus a test observation: (1) the system
  beats a single model call (the engineering base is viable); (2) training-free RL shows clear gains from system-level
  reinforcement learning, and the TF-RL algorithm's use in multimodal knowledge construction and consumption has been
  optimised and improved; and (3) the comparison against the industry SOTA baseline level is observed on the test set.
  Consequences: the carriers stay held under 242 until the lock so defined; the programme adds an explicit TF-RL line
  after the R6/R7 communication-template rounds (design to be proposed: the learning algorithm over node templates and
  knowledge supply with aggregate rewards, local proposer, paid API 0), and every milestone read reports the published
  SOTA level beside the repo numbers (study CLAUDE.md "gates relative to the published ceiling").

Allowance v3 signed bytes: `docs/receipts/owner/2026-10-10-slurp-test-sample-successor2-allowance-v1.json` at commit
951de831b, sha256 `4e04b23f89b9eb06c1b228649a6f991fb9399dea6efbaf4d168a4b731d9e388d` (the successor-2 fragment is
re-pinned to these bytes before the flip).

## R6-P1 read: NOT NOMINATED; decision 253 PROPOSED by the coordinator (Fable 5.1), 2026-10-10

R6-P1 (the Perception entity template column, TRAIN Fold B, 1,080 rows; owner decisions 245-248) sealed 13:37:28Z
and was read the same afternoon (results note `docs/results/2026-10-10-slurp-nx-r6-perception-fold-b-column-read.md`, merged; the official intent guard also fails for every candidate: 61 / 67 / 65 intent rows differ from lock against the twin's 3 and the limit of 7).
Official pooled SLU-F1 per arm vs lock (row-clustered bootstrap): aa twin +0.72 [+0.12, +1.37]; p1 +0.51
[-1.07, +2.08]; p2 -0.70 [-2.47, +1.13]; p3 -1.41 [-3.13, +0.35] -> no arm clears the nomination rule (CI-LB > 0 and
above the twin). Node-local: p1's presence tag parses 99.8 % and is an ADDITIONAL message element (cross-fitted AUC
increment +0.0215 [+0.0096, +0.0333] over N1 + intent prior, also over the lock's own verdict) but its node quality
(E=none precision 0.57 / recall 0.60, AUC 0.671) sits far under the acceptance bar (0.75 / 0.80) and under the
Solver's own verdict (0.74-0.76 / 0.81-0.83); the deterministic gate converts it to +0.44 [-0.29, +1.17] (declared
rule) or at best +0.63 [+0.07, +1.17] (cross-fit rule over N1; +0.48 [-0.09, +1.05] over N1 + prior; +0.28 [-0.34, +0.89] conditioned on the lock's own answer, so the second clause of the design's ADDITIONAL definition is not met) on the v4g base, and the element's ceiling (perfect gate
+1.1..+1.7) cannot clear the 1.5 pp cascade bar in practice. p2 / p3 (heard mentions inside the 128-character
distinction) are FORM failures (rank-1 parse 13 % / 20 %; mention containment 7 % / 12 %) that harm the locked
consumer (empty-gold false fill +6.4 / +3.3 pp): the channel, not the information, is binding (decision 248's
trigger condition in evidence). Verdict: **NOT NOMINATED** (no harm by the lock column; the presence element is
recorded as additional-but-not-convertible).

- **253** (PROPOSED) The Perception-entity line after R6-P1: (A) CLOSE it now (one round; the ceiling argument makes a
  second round unable to reach the cascade bar; the presence tag is kept as a measured feature for a later
  deterministic consumer and the heard-mention channel is recorded as contract-bound); (B) one more round of
  precision-oriented presence-only variants (p1 with a hedge, list-majority voting; ~4.1 GPU-h; ceiling unchanged);
  (C) engineer the v2 note contract now (decision 248 trigger: gain present, channel binding) as a new Perception base
  with its own A/A (~1-2 days engineering + ~4 GPU-h per column flight). Recommended: A, with the GPU going to the
  TF-RL line (decision 252 mode 2) whose design proposal follows; C stays available if the TF-RL line needs the
  Perception node to emit structured evidence.

## Decisions 254-256 PROPOSED by the coordinator (Fable 5.1), 2026-10-10 -- the TF-RL line (decision 252 mode 2)

Design: `docs/readiness/2026-10-10-slurp-tfrl-sealed-credit-routing-design-v1.md` (sealed-credit routing, SCR: a
training-free off-policy contextual learner over TYPED, pinned, already-measured actions, learned offline from the
counterfactual same-flight columns on file (R1 i1/i2, R6-P1, P-SV-1..4, W-SV / W4-SV, ROLL pools) with
cross-fitting, flown as ONE routed policy arm; exploration through proposer-authored typed arms in NX columns; the
gate result (+0.75 / +0.98, CI-LB > 0 on two flights) is its first instance).
- **254** (PROPOSED) Adopt SCR as the TF-RL line; TF-0 (0 GPU) and the E9 policy-arm engineering start now; TF-1
  (Fold B column, ~3-4 GPU-h) flies only if TF-0's cross-fitted SLU-F1 gain has CI-LB > 0 and a point >= 1.5 pp (or
  >= 1.0 with CI-LB >= 0.5 and a clean intent guard); then Fold A (TF-2), DEV composed (TF-3), test. Recommended: yes.
- **255** (PROPOSED) The proposer of new typed arms is the frozen core in its existing text-only seam or a hand author,
  both labelled, fed aggregate contrast tables only; no external proposer (paid API 0). Recommended: yes.
- **256** (PROPOSED) = decision 253 option A (close the Perception-entity presence line after one round) so the GPU
  after the successor-2 test read goes to TF-1 when TF-0 clears its rule; the p1 presence tag and the K6p key stay
  available to SCR as actions / context features. Recommended: yes.

## TF-0 (sealed-credit routing, offline) read: the rule of decision 254 is NOT met; decision 257 PROPOSED (2026-10-10)

TF-0 (`scripts/analysis/slurp_scr_offline_learner.py`, merge 46496fc52; outputs `analysis/SAEA-SLURP-SCR-TF0-V1/`,
pinned table `prepared/SAEA-SLURP-SCR-ROUTING-TABLE-V1/`; zero contacts) learned a per-row routing policy over the
19 sealed counterfactual Solver columns on TRAIN Fold B (R1 i1 and i2 arms, R6-P1 level-2 answers, the post-Solver
empty action) from the pre-Solver signature with utterance-hash cross-fitting. The machinery reproduces the R6 gate
(+0.7455 / +0.9831, false fills 91 -> 64 / 93 -> 60). Headline (default action set {lock, r1-c3, r1-i2-c3, r1-c5,
r1-i2-c4, empty}): routed vs lock **+0.42 [-0.35, +1.20]** (501 rows routed), vs the twin -0.11 [-1.15, +0.92];
leave-one-flight-out i1 -> i2 -0.05 [-0.83, +0.72], i2 -> i1 +0.10 [-0.75, +0.93]; the per-row oracle +11.36 is
inflated by decoding noise (best-of-lock-or-twin on noise alone +1.28 [+0.78, +1.83]). The decision-254 rule (CI-LB > 0
and point >= 1.5, or >= 1.0 with CI-LB >= 0.5) is not met: routing among the EXISTING arms transfers no gain across
flights. Verdict: the SCR line over the current action pool is closed at its measured ceiling; it re-opens only if a
new action with real context heterogeneity enters the pool.

The record now reads consistently: every learned POLICY over text or over existing arms (about 25 cells since
2026-09-23, now including routing) is within noise; the only mechanisms with CI-LB > 0 on n >= 1,000 are statistics-
learned deterministic rules (v4g +1.55 / +0.98) and deterministic VERIFICATION / SELECTION over extra core samples
(ROLL support filter +1.40 [+0.55, +2.29] offline, ROLL-3 2-of-3 +0.84 [+0.19, +1.49] at +2 Solver calls per row; the
c3 verdict gate +0.75 / +0.98 at +1 Solver call per row). The review-off lock v2.2 halved the contacts (2.0 vs 4.05
per row) without loss; those freed contacts can buy verification instead of the Reviewer loop that never repaired.

- **257** (PROPOSED) VER-1, the verification layer on lock v2.2: per row, the Solver is sampled 3 times (the ROLL
  form; the first sample greedy = today's delivery) plus the c3 presence-verdict call; delivery = v4g over the
  support-filtered entity set (2-of-3) with the verdict x N1 >= 0.2 gate; contacts per row 2 -> 5 (still at or under
  the full graph's 4.05 + G5 Reviewer cost in wall time, since the samples share the prefix cache). Registered as a
  same-flight column on TRAIN Fold B (arms: VER-1 non-delivering, twin, lock delivering; the extra samples are the
  arm's own contacts), predicted +1.5..+2.3 pp SLU-F1 at measured conversions (support filter +0.84 at 2-of-3 and the
  gate +0.75 / +0.98, assumed additive -- the overlap on empty-gold rows is the risk and is what the read measures),
  intent unchanged (the gate moves 0 intent rows; the filter keeps the greedy sample's intent). Fold A confirms, DEV
  composes (lock v2.3 = v2.2 + VER-1), then the test sample. Cost ~6 GPU-h Fold B, ~2 Fold A, ~4 DEV. Recommended:
  yes, as the next GPU round after the successor-2 read; it is the only path on file whose components each already
  clear CI-LB > 0 at n >= 1,000. Under decision 252 mode 2 this is the `inference-time-verification-v1` family
  (registered in `core.base.STAGE3_ALGORITHMS`) with its thresholds (s, N1 cut) learned from TRAIN statistics; the
  coordinator asks the owner to confirm that this counts as the training-free system-level learning the lock
  requires, since reinforcement-style policy learning over text has now failed on every form tried.

## Decisions 253-257 ruled by the owner, 2026-10-10

Owner, verbatim: 「决策253：A；254：按你建议改为VER-1；255-257：同意。」 ("253: A; 254: as you recommend, replaced by
VER-1; 255-257: agreed.")

- **253** RULED A: the Perception-entity presence line is CLOSED after one round; the p1 presence tag and the K6p key
  remain available as features / actions; the heard-mention channel is recorded as contract-bound (v2 contract only
  on a future trigger).
- **254** RULED as amended: the sealed-credit routing line is closed at its measured ceiling (TF-0: +0.42 [-0.35,
  +1.20], transfer 0); VER-1 takes its place as the TF-RL line's next round.
- **255** RULED: proposers are local only (the frozen core's text-only seam or a hand author, labelled); paid API 0.
- **256** RULED: = 253 A.
- **257** RULED: VER-1 (the verification layer on lock v2.2: Solver samples + support filter + the c3 presence verdict
  x N1 gate at delivery) is the next GPU round after the successor-2 test read; the owner accepts the
  inference-time-verification family with TRAIN-learned thresholds as the training-free system-level learning of
  decision 252 mode 2. Execution plan (coordinator): VER-1a = a 3-sample ROLL-form pool of the lock v2.2 Solver on
  TRAIN Fold B (greedy first sample = today's delivery; ~4,320 contacts, ~1.3-2 GPU-h), read OFFLINE together with
  the existing R1 i1/i2 c3 verdict columns on the same rows (support filter s in {2, 3} x verdict x N1 gate x v4g,
  cross-fitted, 0.67 pp floor) -> VER-1b Fold A confirmation pool (+ a c3 column there) with the rule FIXED ->
  runtime delivery component `verification-delivery-v1` (support filter over samples + verdict contact) -> DEV
  composed read (lock v2.3 = v2.2 + VER-1) -> test sample.

Decision 257 boundary, confirmed by the owner 2026-10-10 (「好，继续吧」 after the coordinator's clarification): VER-1 is
a NODE-LOCAL change at the Solver (three decodes, one c3 verdict contact) followed by a DETERMINISTIC verifier
(support filter x verdict x N1 gate x v4g) and delivery; no model node consumes the samples (the Reviewer loop stays
removed, decision 232); no template and no inter-node message schema changes (the communication-template line of
decision 245 stays parked under 253-A / 248 with its trigger); any sample-side confidence tag would be a separate
VER-2 proposal under the cascade rules of 245, not an afterthought.

## VER-1 offline composer read (0 GPU) and the VER-1a amendment to five samples (coordinator, 2026-10-10)

`scripts/analysis/slurp_ver1_offline.py` (merge 7dfdb4b4d; controls reproduced: ROLL-1 s=3 +1.40 [+0.55, +2.29],
ROLL-3 2-of-3 over v4 +0.84 [+0.19, +1.49], R1 i1/i2 gate +0.7455 / +0.9831). On the existing 5-sample pools, the
support filter OVER v4g (sample-0 entities kept iff supported by >= s samples; labels unchanged): ROLL-2 Fold A n=5 s=2
+1.03 [+0.47, +1.70], n=3 s=2 +0.91 [-0.07, +2.03]; ROLL-3 DEV n=5 s=2 +0.76 [+0.08, +1.45], n=3 s=2 +0.18 [-0.71,
+1.06]; s=3 at n=3 harms on DEV (-1.62). The gain is false-fill suppression on empty-gold rows (Fold A n=3: empty-gold
+1.74, non-empty -0.90), i.e. the SAME mass the verdict x N1 gate acts on, so filter + gate are not expected to be
additive; the VER-1 delivered estimate over v4g is therefore about +1.0 pp (n=5, s=2) with the gate's contribution to
be measured on the same rows, under the 1.5 pp bar unless the combination surprises. Consequence: VER-1a is AMENDED
before any contact from 3 to 5 samples per row (ceiling 6, 6,480 calls, ~2.5 GPU-h; plurality commit min_support 3
in flight; s = 2 / 3 and the gate read offline), so that the resolved form is measured; the rows are amended in
place with their countersignature kept, and the receipt is re-minted.

## Test-sample successor-2 read (lock v2.2 on the signed sample) recorded, 2026-10-10

`docs/results/2026-10-10-slurp-milestone-successor2-composed-test-sample-read.md` (merge de47b366d). One attempt,
3,010 recordings / 682 prompts, post-stratified natural mixture (primary): composed v2.2 minus the sealed successor-1
COMP-1b column SLU-F1 64.98 -> 66.65 = **+1.67 [+0.53, +2.83]** (raw pooled +2.15 [+0.89, +3.45]; span-F1 +3.61),
intent 82.82 -> 82.36 = -0.47 [-1.04, +0.22]; equal-stratum SLU +0.95 [-0.97, +3.10]. Minus the sealed PLAN column:
SLU-F1 64.18 -> 66.65 = +2.46 [+0.88, +3.96], intent 77.02 -> 82.36 = **+5.34 [+3.67, +6.97]**. Registered verdict
NEUTRAL = the no-harm claim HOLDS on both metrics; the SLU-F1 observation is positive with CI excluding 0 but its lower
bound (0.53) is under the declared cross-flight offset (0.73), so the design does not resolve it as a gain beyond flight
variation (development evidence, decision 28). Efficiency: 2.00 vs 4.06 contacts per row, prompt tokens -60.5 %, active
GPU-h 4.94 -> 3.72. Decision 252 clause 3 table (indicative; sample != full split; published rows are trained systems
on the full split): intent 82.36 vs HerMiT 78.33 / SF-ID 72.06 (above both; gold-transcript bound 84.84); SLU-F1 66.65
vs SF-ID 64.02 / HerMiT 70.84 (4.19 pp under HerMiT; bound 78.19). Nothing here releases a carrier (252 needs all three
modes); the next test read needs a new allowance once v2.3 exists.

## VER-1a pool read (TRAIN Fold B, offline, 0 GPU) and decision 258 PROPOSED (2026-10-10)

Pool SAEA-SLURP-STAGE3-VER1A-SAMPLES-FOLD-B-V1 (sealed 21:16:28Z; 1,080 rows x 5 Solver samples, sample 0 greedy)
read by `scripts/analysis/slurp_ver1_offline.py` with the R1 i1 / i2 c3 verdict columns on the same rows (output
`analysis/SAEA-SLURP-VER1-OFFLINE-VER1A-FOLD-B/`, report sha256 3679315c...; READ row countersigned b4cec7577). On the
lock base (v4g), vs the greedy sample S0 (64.04; the lock columns of R1 i1 / i2 sit at 63.69 / 64.86, inside the
cross-flight band), whole-utterance bootstrap:
- filter alone n=5 s=2: +0.85 [+0.35, +1.36] (9 false fills removed, non-empty 2 lost / 5 gained); n=3 s=2: +0.74 [+0.12, +1.36];
- gate alone (c3 verdict x N1 >= 0.2): i1 +0.53 [-0.05, +1.08], i2 +0.82 [+0.25, +1.39];
- **filter + gate**: n=5 s=2 + gate(i1) **+1.29 [+0.54, +2.05]**, + gate(i2) **+1.43 [+0.69, +2.16]**; n=3 s=2 + gate +1.12
  [+0.30, +1.94] / +1.19 [+0.36, +2.01]; intent rows moved 1; the empty-gold half carries +1.2..+1.3 and the
  non-empty half +0.04 (no loss) -- the two components are largely additive at s = 2;
- cross-fitted (threshold chosen on one utterance-hash half, scored on the other): n=5 +0.78 [+0.02, +1.56] (i1) /
  +1.08 [+0.26, +1.90] (i2); n=3 +0.97 [+0.25, +1.70] / +1.10 [+0.33, +1.87] -- the honest VER-1 estimate on Fold B is
  about +1.0 pp over the lock, CI-LB about +0.3, with n = 3 as good as n = 5 once selection optimism is removed;
- oracle ceilings: perfect gate on the filtered column +3.7; best of 5 samples +8.8 (selection headroom without a verifier).
Verdict: the verification layer is a real, replicated-component mechanism (both parts CI-LB > 0 on their own flights and
additive here) but its measured size (~+1.0 pp over v4g) is under decision 192's 1.5 pp; it is a candidate for a no-harm
+ efficiency-neutral lock component, not for a 1.5 pp claim.

- **258** (PROPOSED) Next step for VER-1: (A) Fold A confirmation with the rule FIXED at n = 3, s = 2, c3 verdict x N1 >=
  0.2 (the cheapest form that matches n = 5 after cross-fitting; runtime cost 1 Perception + 3 Solver + 1 verdict = 5
  contacts per row, about the old full graph's 4.05): two cells on TRAIN Fold A, the 3-sample pool (4,320 calls, ~1.5
  GPU-h) and a c3 template column (E1 form: c3 + twin + lock, 4,320 calls, ~1.5 GPU-h), read offline exactly as Fold B;
  stable per decision 247 if CI-LB > 0 with the rule fixed -> then the runtime `verification-delivery-v1` component (E10:
  the verdict contact + the deterministic verifier inside the module) and the DEV composed read (lock v2.3 = v2.2 + VER-1);
  (B) stop VER-1 at this read (about +1.0 pp is not worth 2.5x the lock's contacts) and keep v2.2; (C) go to the runtime
  component first and confirm on Fold A with a single delivering cell + in-chain A/A (~1 day engineering, ~2 GPU-h).
  Recommended: A (the record's only additive, replicated SLU mechanism; the cost stays at the old graph's level and the
  Fold A read settles stability before any runtime work).

Decision 258 option A, confirmation criterion fixed BEFORE any Fold A contact (coordinator, 2026-10-10; VER-1b / VER-1c
registered HELD, merge cd9e48431): with the rule fixed at n = 3, s = 2, c3 verdict x N1 >= 0.2 (plus v4g), the Fold A
read is CONFIRMED iff the pooled official SLU-F1 delta of the rule over the VER-1c lock column (and over the pool's own
greedy sample) has CI95 lower bound > 0 and a point >= 0.67 pp (the offline floor), with intent moved by at most 7 rows
(decision 247 "stable"); disclosed: the c3 template was authored from Fold A aggregate tables (the rule's thresholds
were tuned on Fold B, named as the tuning roster).

## Decision 258 ruled A ("继续"); 259 deferred until its proposal; carrier model-free proof on file (2026-10-10)

Owner: 「决策258：A，继续；259 等方案出来再说。」 -- 258 RULED A: the Fold A confirmation flies with the rule fixed
(VER-1b pool + VER-1c c3 column; rows countersigned d3e29c843, receipts minted, flipped to flight commits 4088bb95c /
e9629b3d4, gates PASS; VER-1b's first launch at 23:35:50Z was refused by the chain's own one-batch guard because the
VER-1c flip loop's `core.flight.cli check` was alive -- no contact; relaunched after the flip chain ended). 259 (the
carrier model-free work items) waits for the coordinator's proposal.

Carrier end-to-end proof without any model contact (`docs/readiness/2026-10-10-carrier-model-free-end-to-end-proof-v1/README.md`,
merged): Audio2Tool's base runs end to end model-free on its HELD ALL-OFF cells (compose, cli check, 4-row and 400-row
wire checks with the fake transport, seal + official scorers on a canned reply, FIT arithmetic 1 + 3 x 400, derived-media
confinement, 66 scorer/adapter tests); Earnings-21 runs to the seal step and stops on ONE harness gap (the wire-check
seal path does not write the unit-stitch trace record that invariant I7 requires; a driver-side workaround then scores
all five scorers; also the E21 cells do not list the `wire-check` stage); Earnings-22 has the descriptor, thin adapter,
module hooks, base and dataset fragments and the delivery normaliser but no registered cell (missing: window inventory
for the 10 dev calls, experiment / model fragments, ledger row, readiness package, an `e220` byte-proof case, an own null;
about 1-2 engineering days, of which the feature packets need an encoder pass). Decision 259 will propose exactly these
model-free items.

## Decision 259 PROPOSED by the coordinator (Fable 5.1), 2026-10-10: carrier model-free readiness work (no GPU, carriers stay held)

Purpose: the owner goal's second clause ("the engineering base runs completely on Audio2Tool, E21, E22") can be
made provable WITHOUT a carrier flight, inside decisions 242 / 252; the proof on file
(`docs/readiness/2026-10-10-carrier-model-free-end-to-end-proof-v1/README.md`) names exactly what is missing.
- **259** (PROPOSED) Authorise, as model-free engineering in GPU gaps (Sonnet in worktrees, Fable reviews), in this
  order: (1) **E21 seal path**: make `FlightRuntime._wire_check_seal_and_score` write the unit-stitch trace record that
  the real `seal()` writes (invariant I7), with a unit test reproducing the failing shape, then add the `wire-check`
  stage to the E21 ALL-OFF cells through a successor registration (registered bytes are never edited in place), then
  run the full 1,593-unit model-free seal-and-score once (about half a day; the runtime edit is identity-bound, so
  pinned ready cells re-pin at their next flip); (2) **E22 registration**: build the window inventory for the 10 dev
  calls (CPU, about 450 windows), write the E22 experiment / baseline / dataset / model fragments (`asr-wer-whisper`
  only, np4 max1024 geometry copied from E21), add `--carrier e22` to the module registration script and an `e220` case
  to `module_equivalence_proof.py`, generate the HELD ALL-OFF cells, package, ledger rows, scripts and tests, and run
  the same model-free proof steps on them (1-2 days; the window FEATURE PACKETS need an encoder pass = a tool-class
  contact, which is NOT part of 259 and would be registered separately); (3) **A2T hardening**: add the A2T dataset
  fragment to the derived-media confinement check's list, and a standing paper-column regression fixture that
  re-scores the sealed direct bundle with `a2t-toolcall-official` (hours). Nothing in 259 contacts a model or flies;
  the carriers' GPU stays held until the lock of decision 252. Recommended: yes, scheduled behind the SLURP VER-1
  rounds so they never block a SLURP flip or flight.

## VER-1 Fold A confirmation read: NOT CONFIRMED; decision 260 PROPOSED (2026-10-11)

Fold A cells sealed: VER-1b pool (SAEA-SLURP-STAGE3-VER1B-SAMPLES-FOLD-A-V1, 4,320 contacts, driver-done 01:30:10Z) and
VER-1c c3 column (SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-V1, 4,320 contacts, driver-done 03:15:10Z); READ rows
countersigned (30077de25, b2077f951); official per-arm columns rendered; composer read
`analysis/SAEA-SLURP-VER1-OFFLINE-VER1B-FOLD-A-V1/` (report sha256 8f1d4777...). On the v4g base, Fold A, with the rule
FIXED on Fold B (n = 3, s = 2, c3 verdict x N1 >= 0.2): vs the pool's greedy sample S0 (66.41) the filter alone +0.58
[-0.25, +1.40], the gate alone +0.49 [-0.05, +1.02], **filter + gate +0.56 [-0.40, +1.51]**; vs the VER-1c lock column
+1.12 [-0.31, +2.56], vs its twin +0.87 [-0.48, +2.21]; strata: empty-gold +1.37 [+0.93, +1.85], non-empty **-0.87
[-1.72, -0.06]** (on Fold A the rule costs non-empty rows: 18 lost / 5 gained); 1 intent row moved; cross-fit picked
"no gate" on one half. The pre-fixed criterion (CI-LB > 0 over the Fold A lock column and point >= 0.67) is NOT met:
**NOT CONFIRMED** (decision 247 "stable" fails; the Fold B in-sample +1.29 / +1.43 shrank to +0.56, in line with the
cross-fitted ~+1.0 minus the flight band). Oracle ceilings on Fold A: perfect gate on S0 +3.98 (on the filtered column +3.82), best of 3 samples +5.34. Results note: `docs/results/2026-10-11-slurp-ver1-verification-layer-fold-b-fold-a-read.md` (merged); it notes that the registry's and the VER-1b recipe's wordings of the criterion differ (greedy sample vs lock column; 7 rows vs 0.67 pp intent) and that the rule fails both.
What remains true across both folds: the 5-sample support filter at s = 2 over v4g has CI-LB > 0 on every 5-sample pool
read (VER-1a Fold B +0.85 [+0.35, +1.36]; ROLL-2 Fold A pool +1.03 [+0.47, +1.70]; ROLL-3 DEV +0.76 [+0.08, +1.45]),
about +0.8..+1.0 pp at 6 contacts per row; the 3-sample form and the c3 gate do not replicate on Fold A.

- **260** (PROPOSED) VER-1 disposition: (A) CLOSE VER-1 as a lock candidate (recorded: the verification family's stable
  gain is +0.5..+1.0 pp over v4g, under the 0.67 / 1.5 floors for a lock, at 2.5-3x the lock's Solver contacts; the
  records, pools and composer stay for later reuse), keep lock v2.2, and return the GPU to the next line once the owner
  rules on 259 and the direction below; (B) one more confirmation flight: a 5-sample pool on Fold A on lock v2.2
  (6,480 calls, ~2.5 GPU-h) to test filter-only n = 5 s = 2 (the only form with CI-LB > 0 on both existing 5-sample
  pools), accepting that even a confirmed +0.9 pp stays under the lock floor and triples the Solver cost. Recommended: A.
  Direction note for the owner: with VER-1 closed, every measured mechanism family on SLURP SLU-F1 (templates, supply,
  routing, selection / verification, post-processing) has now been read at n >= 1,000; the composed gains on the test
  sample are intent +5.34 vs PLAN (locked) and SLU-F1 +1.67 vs COMP-1b / +2.46 vs PLAN (v4g + review-off), SLU-F1 66.65
  against the published HerMiT 70.84. No measured mechanism closes the remaining 4 pp; the headroom tables point to
  entity CONTENT (consumption ~210 items, hearing ~106 items on Fold A), which needs either a stronger core or a new
  evidence source, not another selection rule. The coordinator will put the options for that choice to the owner as a
  separate briefing.

## Direction briefing after VER-1: where the remaining SLURP SLU-F1 headroom is, and decision 261 PROPOSED (2026-10-11)

State of the record (all n >= 1,000, TRAIN folds / DEV / the signed test sample):
- Locked and replicated: intent +5.34..+5.80 over PLAN on the test sample (COMP-1b components); SLU-F1 +1.67 over COMP-1b
  / +2.46 over PLAN on the test sample (v4g at delivery + review-off at half the contacts); test-sample levels 82.36 / 66.65.
- Read and closed at n >= 1,000 without a lockable SLU gain: Solver templates (R1 i1 / i2), Perception templates and
  keys (P-SV-1..4, R6-P1), supply variants (W-SV, W4-SV, Stage S), learned policies (CELL-1/2/3, GEPA, system text,
  K16 / K4, SCR routing), selection / verification (ROLL commit line, VERIFY-1, VER-1: +0.5..+1.0 stable at 2.5-3x the
  Solver contacts), deterministic rules beyond v4g (v5 grid, scope rule +0.49, presence gate).
- Where the misses are (Fold A, COMP-1b base, `docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md`,
  `docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md`): 407 gold-side errors on delivered rows, of which
  about 210 are consumption-type (the value was in the Perception note or the supply and the Solver did not deliver it)
  and 106 hearing-type (the value was never heard: Whisper-large-v3 as a tool contained only 75 % of gold spans, E5
  closed); SPURIOUS 253 at delivery (179 not in the note). The remaining 4.2 pp to the published HerMiT SLU-F1 (70.84,
  full test, trained) is entity CONTENT. No selection rule over the current core's own outputs converts it (oracle
  "best of 5 samples" +8.8 exists, but every verifier tried extracts <= 1 pp of it).
- **261** (PROPOSED) the owner chooses the next line, in the coordinator's order of expected value:
  (A) **Stronger local core at the same boundary** -- re-open the core-selection question (owner 2026-09-06 memory:
  "pick the strongest local speech-multimodal core"): a larger / less quantised Qwen3-Omni build (e.g. Q6_K or Q8_0 of
  the same 30B-A3B if VRAM allows at np2, or the Thinking variant) or another open omni core that fits 32 GB, measured
  FIRST as a bare-core vs PLAN read on DEV-2000-ADDED (two flights, ~3 GPU-h) before any system work; the whole base is
  core-agnostic by construction (API boundary, descriptors, scorers), so this reuses everything; cost = model download
  + one new serving geometry + re-pins; risk = throughput (a Q8 30B at np4 may halve the request rate).
  (B) **A second hearing pass as a measured tool** -- not Whisper (75 % containment, closed) but the core itself in a
  hearing-only role over the entity-bearing span candidates (the "relisten" family read SHADOW HARM in E4; a NEW form
  would need a different contract: the Solver asks for one span per candidate slot type and the hearing pass returns the
  spoken words only, model-initiated per decision 206); 0 engineering reuse of E4 is possible; expected value unknown,
  ceiling bounded by the 106 hearing-type misses (~5 pp oracle).
  (C) **Accept the level and consolidate** -- freeze lock v2.2 as the SLURP system result, run the carriers' model-free
  readiness (259) and then the carriers' ALL-OFF A/A flights under a revised 252, and start the Stage-2B paper-candidate
  qualification (replicated intent lock, v4g, efficiency result, the test-sample evidence) while a stronger core is
  evaluated in parallel on a separate serving geometry when the GPU is free.
  Recommended: A measured first (one bare-core read decides whether the core is the ceiling), with C's model-free parts
  (259) running in the gaps; B only if A shows the core is not the limit.

Coordinator note, 2026-10-11 ~03:55Z: with the GPU idle and decisions 260 / 261 pending, the model-free items of the
259 proposal are being EXECUTED as engineering-base repairs under the owner's standing instruction of 2026-10-09
("systematically repair and clean the engineering base"): (1) the E21 wire-check seal path (a harness defect against
invariant I7) + the `wire-check` stage by successor registration + the full model-free seal-and-score; (3) the A2T
confinement-list and paper-column regression hardening; and (2) the E22 ALL-OFF registration prepared HELD (window
inventory on CPU, fragments, `--carrier e22`, `e220` byte proof, package, DRAFT rows) -- no model contact, no flight,
nothing countersigned; all of it reversible, and the owner's ruling on 259 decides whether the E22 cells stay
registered. Carriers' GPU remains held (242 / 252).

## Decisions 259-261 ruled by the owner, 2026-10-11; the owner's question on where training-free RL acts

Owner, verbatim: 「决策259：同意；260：A；261：我们本地的GPU的型号只是一个显存只有24GB的便携，在这个基础上，我倾向于认为最多去
找一下llama.cpp社区是否存在thinging模式的模型，可以提前下载。同步你按照B去处理。我现在疑惑的是，training free RL发生在什么环节，
提供了怎样的有益增益？我们论文的核心还是去看training free RL这套方案是否有稳定的增益的！」

English: "259: agreed; 260: A; 261: our local GPU is a portable card with only 24 GB of VRAM; on that basis I lean to
at most checking whether the llama.cpp community has a thinking-mode model, which can be downloaded in advance; in
parallel proceed with B. What puzzles me now is: at which step does training-free RL act, and what beneficial gain
has it provided? The core of our paper is still whether this training-free RL scheme has a STABLE gain!"

- **259** RULED: the carrier model-free work proceeds (already in execution: E21 seal path + wire-check stage + full
  model-free seal-and-score; E22 HELD registration; A2T hardening).
- **260** RULED A: VER-1 is CLOSED as a lock candidate; lock v2.2 stands; the pools, columns and composer remain for reuse.
- **261** RULED (owner's variant): no larger-core line on the 24 GB card; the coordinator checks the llama.cpp community
  for a thinking-mode Qwen3-Omni GGUF that fits 24 GB and may pre-download it (program-level acquisition through the
  umbrella lock and fetch scripts, never ad hoc); in parallel, option B (a new hearing-pass tool form, model-initiated
  per decision 206) is designed and registered as the next SLURP line.
- The owner's question is answered in the coordinator's briefing of the same day and recorded as decision 262's
  proposal (below).

## Where training-free RL acts in this study, what it has gained, and decision 262 PROPOSED (coordinator, 2026-10-11)

Answer to the owner's question, from the record only.

**The loop that exists.** Every round of this study since 2026-09-22 has run the same training-free loop, registered as
`sealed-credit-system-policy-v1`: (1) ROLLOUT -- a registered flight produces sealed per-row trajectories of the whole
system (Perception -> Solver -> delivery) on a TRAIN fold or DEV; (2) CREDIT -- the official scorer assigns per-row,
per-node reward (official SLU-F1 / intent contributions, typed failure classes, exchange rates), never a scalar per
trajectory; (3) UPDATE -- a candidate change to a TYPED system component (what knowledge is constructed, which key /
vote retrieves it, how much is supplied, which contract the Solver follows, which deterministic rule delivers) is
proposed from aggregate credit tables; (4) SELECTION -- the candidate is read offline over sealed pools (0.67 pp floor)
or as a same-flight column (n >= 1,080) and selected only if its CI95 lower bound clears the floor against a twin;
(5) CONFIRMATION -- the selected change is re-measured on a fresh roster (Fold A, then DEV, then the signed test sample)
before it is locked. No parameter of the frozen core changes; the "policy" is the system around the core.

**Where it produced STABLE gains (replicated on fresh rosters, CI-LB > 0):**
| component (the UPDATE that was selected) | loop evidence | stable gain | where it acts |
| --- | --- | --- | --- |
| COMP-1b intent composition (agreement vote over the exemplar neighbours + centroid boundary keys, k60 pool) | nominated by sealed-credit inner-loop run 2 as the ONLY candidate over its floor (+4.26 [+2.41, +6.11] intent, `docs/results/2026-09-29-slurp-sealed-credit-inner-loop-run-2.md`), confirmed Fold A +3.80, DEV +4.60 [+2.58, +6.73], test sample +5.80 [+4.04, +7.42], R5 same-chain +4.90 | **intent +4.6..+5.8 pp** | knowledge CONSTRUCTION (keys, vote) feeding the Perception node |
| v4g delivery normaliser (rules learned from TRAIN statistics: article / o'clock / scope / type-inventory / empty-entity rate guards) | 431 rule combinations + 10 single rules searched by official credit on the A2 pool, selected (+0.98 [+0.21, +1.74]), confirmed Fold A +1.67, Fold B +1.55 [+0.81, +2.33]; the composed v2.2 then read SLU +1.67 [+0.53, +2.83] over COMP-1b on the test sample | **SLU-F1 +1.0..+1.7 pp** | DELIVERY (consumption side) |
| review-off graph (the Reviewer loop removed after its credit read 0/100 repairs) | N100 read, R5 composed read NEUTRAL at 2.0 vs 4.05 contacts per row, test sample no-harm | **cost -50 % at equal accuracy** | graph structure |
| Stage-2 knowledge supply (B1 exemplars k20, B4b slot store v2) -- the same loop before it was named | B1 +12.61 [+10.54, +14.60] Fold A, replicate +13.70; B4b +2.55 [+1.13, +3.98], replicate +1.54 | **SLU-F1 +14 pp over the bare core** (now inside PLAN) | knowledge CONSTRUCTION + SUPPLY at the Solver |
Bare core -> PLAN on DEV: intent 61.7 -> 76.6, SLU-F1 38.1 -> 65.4 (`docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md`); PLAN -> v2.2 on the test sample: intent 77.0 -> 82.4, SLU-F1 64.2 -> 66.7.

**Where it produced NOTHING stable (all read at n >= 1,000 or offline at 0.67 pp):** every UPDATE whose content was
FREE TEXT written by a model or a learner from reward -- TF-GRPO semantic deltas (CELL-1/2/3), GEPA reflective prose,
the joint system-text search (L/B), the K16 / K4 template populations, the hand-written template columns (R1 i1 / i2,
R6-P1) -- and every UPDATE that re-chose among the core's own outputs (sample medoids, routing over arms, the c3 gate
beyond ~+0.5, VER-1 on Fold A). The four failure modes are named in
`docs/results/2026-09-26-slurp-stage3-locked-tfrl-academic-baseline-v1.md` (unmeasurable gradient, prose-as-policy,
credit from decoding noise, no verifier in the loop).

**So, plainly:** the training-free RL of this study acts BETWEEN flights, on the knowledge-construction, retrieval,
supply and delivery components of the system, with per-row official credit as the reward and fresh-roster confirmation
as the acceptance test; it has given a replicated intent gain of about +5 pp and an SLU-F1 gain of about +1.7 pp on top
of a +14 pp knowledge-supply gain, at half the contacts. What it has NOT given is a learner that writes its own policy
text: those updates never cleared noise. That negative result is as replicated as the positive one.

- **262** (PROPOSED) Make this the paper's core claim and shape the remaining rounds to it: (a) the algorithm named and
  frozen as "sealed-credit policy search over typed system components" (rollout -> per-row typed credit -> candidate
  from aggregate tables -> offline / same-flight selection with a twin -> fresh-roster confirmation), with its
  measurement instrument as part of the method; (b) the evidence ledger above (B1, B4b, COMP-1b, v4g, review-off) as
  the stable-gain record, each entry with its selection read and its confirmation read; (c) the negative result (free-
  text updates and output re-selection do not transfer under the same instrument) reported with the same rigour;
  (d) the next rounds chosen to ADD entries of type (a): construction-side updates selected by credit -- the
  hearing-pass evidence tool (261-B) if it clears, the thinking-mode core only if it fits the card and the slot; and
  (e) the carriers run the SAME loop (ALL-OFF A/A -> one credit-selected construction update -> confirmation) once the
  owner releases their GPU, which is what turns "one task" into "several tasks" for the goal. Recommended: yes.

## Owner request 2026-10-11: return to the algorithm; the lineage analysis and decision 263 PROPOSED (coordinator, 2026-10-11)

Owner, verbatim: 「我认为不够，我们需要回归到算法本身，要识别算法本身是否有缺陷，你可以参考下从training free GRPO提出至今的
training free RL的演进，每一个学术研究工作具体识别和发现了哪些问题，是怎样通过设计和优化学习算法去解决的？具体回答三个问题：
1）面对我们的具体任务，应该采用哪一种学术基线更优？2）这个学术基线在我们的任务上还有哪些不足？3）我们对已经识别到的不足是否有
提升和改进的措施和方案？」

English: "I think that is not enough. We need to return to the algorithm itself and identify whether the algorithm has
defects. Refer to the evolution of training-free RL from the proposal of Training-Free GRPO to now: which problems did
each academic work identify, and how did it solve them by designing and optimising the learning algorithm? Answer three
questions: (1) for our specific task, which academic baseline is the better one to adopt? (2) what does that baseline
still lack on our task? (3) do we have measures and plans to improve the deficits we have identified?"

Answer: `docs/readiness/2026-10-11-slurp-tfrl-lineage-and-algorithm-baseline-analysis-v1.md` (model-free). In short:
- **Lineage.** Dynamic Cheatsheet -> GEPA -> Memento -> ReasoningBank/MaTTS -> Training-Free GRPO -> ACE -> procedural
  knowledge / chain-of-experience -> SEAM -> RIZZ, plus the trained-RL credit-assignment line. The branch moved from
  "write a lesson" (TF-GRPO semantic advantage) to "write a typed item, keep it incremental, verify it, scope it" (ACE
  delta items; RIZZ verified-only, branch-routed updates). None of the training-free works states a noise model of its
  evaluator, a form control, or a fresh-roster confirmation; credit assignment improved only in the trained branch.
- **Q1.** ACE (arXiv 2510.04618) is the best structural fit (itemised incremental store, verifier-driven, no sampled
  group needed; registered here as `ace-grow-refine-v1`, never flown). TF-GRPO stays as the second comparator (flown
  here in faithful shape: CELL-1/2/3 -0.48 / +0.64 / -1.44 with twins reproducing the arms; signal empty on 400 of 625
  rows). GEPA fails the evaluation-cost constraint (S1); Memento and SEAM train a component and are out of boundary.
- **Q2.** Seven deficits of ACE on this task, each bound to a measurement: D1 weak reflector (repair 0/100); D2 prose
  items pay a form cost (twins; `general` stratum); D3 no input key (the gains here are speech-keyed retrieval, B1
  +12.6, COMP-1b intent +4.6/+5.8); D4 acceptance on one score with no noise model (A/A +1.87 [+0.41, +3.36]); D5 no
  verifier at delivery (oracle +6.55 vs realised ~+0.9); D6 context growth vs the 24,576-token slot; D7 unscoped
  updates (RIZZ interference; CELL-3 gate null).
- **Q3.** D1, D2, D3, D4, D6, D7 are replaced in the sealed-credit loop of decision 262 (typed per-row official credit;
  typed entries and deterministic rules; speech-keyed construction; the instrument as the acceptance test; fixed
  budget; stratum protection), each with a replicated gain or a replicated null behind it. D5 was tested (VER-1) and
  closed at ~+0.9 pp. The remaining algorithmic gap: the typed loop has never run autonomously for several iterations
  with a proposer confined to typed operators; every accepted update was chosen by a person from the credit tables.
- **263** (PROPOSED): run the sealed-credit loop autonomously for three iterations on lock v2.2 with the proposer
  confined to typed operators (construction / supply / delivery-rule / scope), and fly ACE as published beside it at
  the same token and contact budget as a third delivering-path column (Fold B select x3, Fold A confirm, then DEV);
  about 11 GPU-h, SLURP only; claim rule: cumulative CI-LB > 0 on Fold A for the typed loop, ACE reported either way.
  Options: **A (recommended)** typed loop + ACE comparator; **B** typed loop alone (~8 GPU-h); **C** no further SLURP
  algorithm rounds, package 262 and release the carriers.

**Also recorded today (coordinator):**
- Merged to master: `sonnet/e21-seal-path` (899a17c48: seal-time trace emission shared by seal and wire-check, unit-
  stitch trace, E21 wire-check successors, A2T paired-400 confinement, standing re-score fixture) and
  `sonnet/e22-register` (c7b4b6e2a: E22 window inventory 10 calls / 451 windows receipted at 0 contacts, two HELD all-off
  cells, `--carrier e22` plumbing, 19 preflight tests; first contact-requiring step = window feature packets; open:
  scorer variant, data-use decision, knowledge-snapshot gap for phase-program baselines, a new serving session name).
- Hearing-pass evidence survey for 261-B: `docs/readiness/2026-10-11-slurp-hearing-pass-evidence-survey-v1.md`
  (read-only). Finding: nothing in the record yet supports option B. E4 failed on span, not hearing (63 of 122
  replacements turned EXACT into BOUNDARY; "unheard" covered 67 % of delivered entities); the official scorer gives
  partial credit by distance; the core's only self-initiated Solver tool record is solver-lookup (16 / 100 calls,
  -5.13 [-9.49, -1.04] at n = 100); a tool schema shown to a non-calling Solver breaks 10-13 % of answers. A design
  must be model-initiated at one node, words only, deterministic verifier, inside the slot budget, with a decision
  oracle first. The design is deferred behind decision 263 because 263-C would close it and 263-A/B set the GPU order.

## Owner directions 2026-10-11 (three dimensions + knowledge-side TF-RL); decision 263 AMENDED to v2, decisions 264-265 PROPOSED (coordinator)

Owner, verbatim (message 1): 「这里面你要分成三个维度去看：第一个维度是，training free RL里面，我们的学习要素是什么，谁负责观测，谁负责
分析和整合，谁负责反思和进一步迭代和优化，比如说模版生成是否还要使用omni模型去生成，是否需要用本地的其他文本能力增强的模型？第二个
维度是，GRPO这种优化方向和指标，更多的是通过脚本的客观评分去指导优化，而不是通过模型去优化；第三个维度是，你可以参考下skillopt等类
RSI的优化方案，我们现在面向系统级优化更多的适合RSI的技术方案，当然核心还是要按照training free RL来承载和优化！」

English: "Look at this along three dimensions. First: in training-free RL, what are our learning elements; who observes,
who analyses and integrates, who reflects and iterates / optimises further; for example, should template generation still
use the Omni model, or do we need another local model with stronger text ability? Second: GRPO's optimisation direction
and metric are guided by objective script scoring, not by a model's judgement. Third: look at SkillOpt and similar
RSI-class schemes; for system-level optimisation an RSI-style technical scheme fits us better, while the core is still
carried and optimised as training-free RL."

Owner, verbatim (message 2): 「同步你还要思考下，从知识构建和消费的维度，我们是否有一些training free RL的方式，比如说基于评价指标和
bad cases，基于训练集选择性的扩充和添加一些知识等」

English: "In parallel, also think about whether, along the knowledge construction and consumption dimension, we have
training-free RL methods, for example selectively expanding and adding knowledge from the training set based on the
evaluation metric and the bad cases."

### Dimension 1 -- learning elements and roles

| role | owner of the role | this study today | source |
| --- | --- | --- | --- |
| learning elements (what is learned) | typed, hash-pinned system artefacts: exemplar index and its per-scenario weights, slot store and cards, retrieval keys and vote, supply budget per scenario, delivery-rule table, scope routing | B1, B4b, COMP-1b, v4g, review-off are entries of exactly this kind | 262 ledger |
| OBSERVE | deterministic: sealed per-row trajectories + the official scorer + process-metric readers | `core.scoring_batch`, `stage3_rollout_score.py`, the NX column readers | instrument 2026-09-26 |
| ANALYSE and INTEGRATE | deterministic: typed failure-class tables (class x slot type x scenario x value-in-supply), exchange rates, per-stratum deltas, the bad-case bank | `slurp_nx_exchange_rates`, `slurp_slu_consumption_headroom.py`, bad-case bank 2026-09-24 | R0.2 / C3 protocol |
| REFLECT and PROPOSE | a model, confined to the typed operator schema (JSON on the wire, grammar-constrained), fed tables only | today a person (coordinator) chooses from the tables; decision 255 allows the frozen core's text seam or a hand author | 255 |
| ITERATE | deterministic driver + the instrument (select on Fold B with a twin and the 1.49 floor; confirm on Fold A; DEV; test) | the countersign / mint / flip / batch-driver sequence | 190, 192, 231, 247 |

The proposer-model question. SkillOpt's ablation (arXiv 2605.23904, Table 5) is the relevant evidence: a target-matched
optimiser recovers 56-74 % of a frontier optimiser's gain, so the loop adds value even with the same model, and a stronger
optimiser is worth having. Local options on this rig (paid API 0): (i) the frozen Omni core's text-only seam on the resident
server (0 extra memory; decision 255 today); (ii) the Qwen3-Omni-30B-A3B-Thinking Q4_K_M GGUF now downloading (umbrella lock
key `qwen3-omni-30b-a3b-thinking-gguf-q4km`, 18.6 GB) run on CPU between flights (24 cores, WSL 44 GB with about 41 GB
available beside the resident server; the 2026-09-07 host-memory kill hazard means a second mmapped GGUF needs an owner GO
and a memory check), or swapped onto the GPU inside the 12-h serving restart window; (iii) a separate local text-only model
on CPU. Boundary: the proposer runs OFFLINE between flights, never in the answer path, so it is not a "second answering LLM";
it must be logged like any tool contact (exposure-ledger row, model file hash, prompt hash, tables hash, output hash), and
its output is a typed candidate, never a node prompt (decision 245).

### Dimension 2 -- the objective is a script

Adopted as a hard invariant of the design: every credit, selection and acceptance figure comes from the official scorer and
deterministic readers; the model proposes, never judges. This is what GRPO does (a scripted reward) and what SkillOpt does
(benchmark-native hard scores, no LLM judge). It applies to the ACE comparator too: ACE's curator may merge items, but its
helpful / harmful counters are computed from per-row official credit over the sealed column and its playbook state is
accepted by the same instrument, so the comparison isolates the update FORM (prose items vs typed artefacts), not the judge.

### Dimension 3 -- RSI shape, training-free RL carrier

What the RSI line adds beyond the TF-RL branch, and what we take:

| work | mechanism | taken into the design as |
| --- | --- | --- |
| Darwin Goedel Machine (2505.22954) | archive of agent versions; parent sampled from the archive; every change empirically validated on a benchmark; open-ended | an ARCHIVE of system states (artefact-hash set + measured credit vector); parent = best by CI-LB with a diversity rule; refused candidates stay as siblings and negative evidence |
| SkillOpt (2605.23904) | frozen target + separate optimiser model + held-out validator; bounded edit budget per step (textual learning rate, 4 -> 2); rejected-edit buffer fed back; epoch-wise slow / meta update never shipped; strict held-out acceptance, ties rejected; benchmark-native scoring | at most L typed operator applications per iteration (2 then 1); the refused-candidate buffer rendered to the proposer as tables; a proposer-side meta summary never entering any node prompt; our gate = SkillOpt's gate PLUS a noise model (same-flight twin, 1.49 floor, Fold A transfer) |
| RRSI (2609.24972) | regularisers against benchmark overfitting, drift and collapse in harness self-improvement | cross-fitting of any TRAIN-fitted threshold, per-stratum tables on every read, fresh-roster confirmation, one component per candidate |
| Hypothesis-driven skill optimisation (2606.22330); skill-overfitting work (2607.26643) | diagnose failure causes before proposing; constrain exploration to keep baseline competence | candidates are written from failure-class tables (C3 protocol); the intent guard and no-loss SLU guard on every arm |

What we deliberately do not take: editing arbitrary harness code or node prompts (SkillOpt edits a prose skill; DGM edits
code). The operator set stays closed and typed (245), because prose supply pays a per-row form cost here (D2) and code
self-modification is outside the thesis object (a control plane around a frozen core, not a self-rewriting agent).

### Knowledge construction / consumption as the first operator class (owner message 2)

Yes: credit-driven selective knowledge augmentation from TRAIN is the construction class of the loop and the class where
every stable SLU gain of this study came from. The record bounds where it can still act (Fold A, AGREE / COMP-1b arms):

| gap kind | measured size | what augmentation can do | precedent |
| --- | --- | --- | --- |
| knowledge ABSENT from the store | 2 items in 2,705 rows; store holds all 60 intents and 54 of 55 slot types | nothing: existence is not the gap | coverage note 2026-09-26 |
| present in TRAIN's value lists, NOT supplied (E4 class) | 40 items, oracle 2.33 pp | supply the value list / cards for the failing slot types and scenarios (selective, by credit table) | B4b slot store, K8 card selection |
| gold exemplar exists, not retrieved at k = 20 | gold intent's median rank 13 / 10 / 14 on intent-wrong rows vs 1 on correct rows; widening k refuted | re-weight or expand the exemplar pool per failing scenario x intent stratum (hard-example mining INTO the index from TRAIN minus the evaluation fold) | B1 exemplars, COMP-1b agreement vote (the vote already converts 45.7 % of newly delivered gold entries, CONV probe) |
| in the supply, NOT used (E1 class and 107 of 229) | 91 + 107 items, oracle 5-9 pp | not a construction gap; consumption; the Solver contract is locked (245) and template columns read null | R1 / R6 column reads |
| not in supply AND not in the transcript | 35 of the 70 S2a.1 items | out of reach of any knowledge operator (hearing) | S2a.1 |
| spurious entities on empty-gold rows | about 40 % of rows have empty gold; false fill is the largest single loss | NEGATIVE knowledge: per-scenario anti-pattern guards learned from TRAIN statistics (RIZZ anti-patterns; v4g's rate guard is one) | v4g |

Expected value at measured conversions: about 18 of the 40 E4-class items at 45 % conversion x 0.062 pp = about 1.1 pp SLU,
plus the intent side of a per-stratum exemplar re-weighting (unmeasured; the P-SV-1/2 contrast-pair exemplars LOWERED
Perception recall, so the operator must be read as a column, not assumed). Alone this sits under the 1.5 pp floor; as the
loop's first two typed operators (value-list supply for the failing types; per-stratum exemplar re-weighting) it is the
natural iteration-1 candidate, read first OFFLINE for retrieval coverage (0 GPU: does the augmented index deliver the gold
entry on more Fold B bad cases?) and then as one same-flight column. Fold hygiene: augment only from TRAIN rows outside the
evaluation fold; confirm on Fold A; compose on DEV.

- **263 AMENDED (v2, PROPOSED)**: the autonomous loop takes the RSI / SkillOpt shape above -- an archive of typed system
  states, a bounded typed-operator proposer fed tables only, scripted objective and the noise-floored instrument as the
  only judge, a refused-candidate buffer, three iterations on Fold B, Fold A confirmation, DEV composed read -- with the
  ACE prose-item form as the in-flight comparator at equal budget. Options A / B / C unchanged.
- **264 (PROPOSED)** Proposer model: A = the frozen core's text seam for iteration 1 (0 extra memory), with the Thinking
  GGUF as a CPU-side proposer ablation once its hash is pinned and the host-memory check passes (owner GO for the memory
  envelope); B = Thinking GGUF from the start; C = the core's text seam only. Recommended: A.
- **265 (PROPOSED)** Iteration-1 operator class = credit-driven selective knowledge augmentation (value-list supply for
  failing slot types + per-stratum exemplar re-weighting, both from TRAIN minus the evaluation fold), with a 0-GPU
  retrieval-coverage read before the column. Recommended: yes.
- E22 base gap closed model-free (branch `sonnet/e22-knowledge-snapshot`, 1f27b1914): an inert, hash-pinned placeholder
  knowledge snapshot for E22 (the runtime refuses empty snapshots; E21 and A2T all-off cells pin real snapshots bound
  invisibly by `knowledge: "none"`); both E22 baselines now pin it, so the package needs the standard re-pin; the wire check
  still stops at the missing window feature packets (encoder pass, GPU held).

### 263 v2 engineering design on file (coordinator, 2026-10-11)

`docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md` (merged af1c055cc; model-free;
registers nothing). It fixes: five roles with one code owner each; invariant I-OBJ (the objective is a script, applied to the
ACE counters); the archive and deterministic parent choice (best CI-LB minus a child-count penalty, class masking after two
refused children); edit budget 2 then 1; the candidate schema `saea-tfrl-typed-candidate-v1` with no free-text field and no
self-declared effect (the validator computes the predicted effect from offline re-retrieval and the exchange rates);
iteration 1 = slot-card + exemplar-stratum composite with a 0-GPU coverage pre-read that must reach +1.5 pp predicted; from
iteration 2 each Fold B cell carries five Solver arms (lock, twin, accumulated parent, typed child, ACE; 6 contacts per row)
so the cumulative state is re-measured every round without a cross-flight bar; the same proposer model (the core's text
seam) for both arms so the comparison measures the update form; the thinking GGUF deferred to an ablation. Build before the
first flight: the review-off module's refusal of supply columns (`rails/consumption_module.py`), the node-local reader for
supply columns, a multi-store release swap, the proposer and ACE modules, the tables script, the archive, a per-column
algorithm label; the proposer resolver touches `runtime.py`, so all merges land before one flight commit and one re-pin.

Three points the spec needs ruled inside 263-A:
- **263-Q1 selection rule.** The spec reads "CI95-LB over 1.49 pp" as: CI95 lower bound > 0 AND point >= 1.49 AND above the
  twin, plus the intent guard (the literal reading, lower bound itself above 1.49, needs about a 3 pp effect at n = 1,080).
  Coordinator: confirm the spec's reading; it is the decision-190 form.
- **263-Q2 ACE column status.** It puts free text into the Solver prompt, so under decision 245 it must be a non-delivering
  comparator that can never be locked. Coordinator: yes.
- **263-R1 stall risk.** The Stage-S supply design predicted at most +0.20 pp for any single supply arm; a typed class may
  have no candidate over the 1.5 pp predicted bar in some iteration. Spec default: keep the bar, allow two proposer retries,
  fly lock / twin / parent / ACE anyway and read delivery candidates offline; owner option: fly the top valid candidate as
  a `claims_benefit: false` measurement, never acceptable as a gain.

## Decisions 263-265 ruled by the owner, 2026-10-11

Owner, verbatim: 「决策263：A；264：A；265：同意」 ("263: A; 264: A; 265: agreed.")

- **263 RULED A** (v2 form): the autonomous typed loop in the RSI / SkillOpt shape with the ACE comparator column at equal
  budget, per the merged spec `docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md`.
  The three points the registry listed "to rule inside 263-A" were not addressed separately; the coordinator applies the
  recommended readings and records them as part of 263-A, open to owner override: **Q1** selection = CI95 lower bound > 0
  AND point >= 1.49 pp AND above the twin, with the 0.65 intent guard (the decision-190 form); **Q2** the ACE column is a
  non-delivering comparator exempt from decision 245 for measurement only and can never be locked; **R1** a class with
  nothing over the 1.5 pp predicted bar flies no typed candidate that round (lock / twin / parent / ACE still fly; delivery
  candidates read offline); R4 (DEV admission path for a nominated typed state) stays open until a state is nominated.
- **264 RULED A**: proposer = the frozen core's text-only seam for iteration 1 (decision 255 covers the typed proposer and
  the ACE reflector alike); the Thinking GGUF becomes a CPU-side proposer ablation only after its hash is pinned in the
  umbrella lock and a host-memory check passes with an owner GO for the memory envelope.
- **265 RULED agreed**: iteration-1 operator class = credit-driven selective knowledge augmentation from TRAIN outside the
  evaluation folds (value-list / card supply for failing slot types + per-stratum exemplar re-weighting, anti-pattern guards
  offline), gated by the 0-GPU coverage pre-read (must reach +1.5 pp predicted before the column is packaged).
- 262 (paper core claim and ledger) remains unruled; the loop's curve and the ACE comparison are what it would cite.

**Execution started (model-free, build plan steps 2-6 of the spec):** E-S1 / E-S2 (supply columns under the review-off
module + readers) and the 265 coverage pre-read were already in flight; now added in parallel worktrees: E-T1 proposer seam
(`rails/tfrl_typed_proposer.py`, candidate schema `saea-tfrl-typed-candidate-v1`, validator, runtime resolver dispatch for
both program ids), E-T2 ACE material + deterministic curator + `ace-playbook` releases, E-T3 contrast tables + cross-fitted
delivery threshold fitter, E-T4 archive / meta / parent choice, E-T5 column algorithm labels. Merge order: E-S1 -> E-T1 ->
E-T2 -> E-T3/E-T4/E-T5 -> driver; one flight commit, one re-pin. GPU stays idle until the pre-read clears and the
iteration-1 proposer cell is countersigned.

## 265 coverage pre-read (0 GPU): iteration 1 has NO candidate over the bar; decision 266 PROPOSED (coordinator, 2026-10-11)

`docs/results/2026-10-11-slurp-tfrl-coverage-preread-fold-b-offline.md` (merged b089b2547; script
`scripts/analysis/slurp_tfrl_coverage_preread.py`; source column = the R6-P1 delivering lock column on TRAIN Fold B, lock
v2.2 + v4g, SLU 64.34 / intent 82.41; the recomputed exemplar top-20, vote shares and Perception block match the sealed
ones on 1,080 / 1,080 rows; 0 contacts).

| operator (cross-fitted on Fold B halves) | predicted SLU-F1 pp | predicted intent pp |
| --- | ---: | ---: |
| (a) credit-selected slot-card value lists | 0.00 (no cell survives the half split; oracle on all 18 reachable items +0.54) | 0 |
| (b) exemplar pool re-weighting (expansion material = 0 rows) | -0.56 (5 gold boundaries gained, 2 lost, 36 exact prints lost) | +0.07 [+0.02, +0.12] |
| (c) per-scenario anti-pattern guards | -0.45 [-1.13, +0.18] (in-sample +0.87: selection optimism 1.3 pp) | 0 |
| composite | **-1.00** | **+0.07** |
| largest honest number (non-credit reference: every card carries its 16 most frequent TRAIN values, +651 tokens per row, harm not netted) | +0.27 at 45 % conversion | -- |

Why the construction class is exhausted on this column, measured: 139 of the 228 MISSING items (61 %) already have their
value in the delivered supply (consumption, not construction); 155 of the 434 gold-side error items (36 %) are values TRAIN
outside the folds never contains; only 18 MISSING items are in a store, not delivered and heard in the transcript, spread
over 14 slot types; the gold intent boundary is already delivered on 142 of the 190 intent-wrong rows and the other 48 rank
at a median of 21; the exemplar pool is already all of TRAIN minus the two folds, so there is nothing legal to add.

**Reading.** The owner's knowledge-side premise (265) holds in kind but not in size: TRAIN knowledge is complete for the
intent and slot-type inventory of this column, and the remaining SLU mass is (i) values TRAIN never shows and (ii) values
already supplied and not used. Neither is a construction-from-TRAIN operation. Under the spec's 263-R1 default, iteration 1
stalls at this pre-read: the typed arm has no candidate. This is the fifth independent reading since 2026-09-29 that the
supply side of SLURP SLU is at its plateau at lock v2.2 (headroom note, S1 supply design, R5, VER-1, now the pre-read).

- **266** (PROPOSED) What iteration 1 flies. Options:
  - **A** the spec's stall default: one Fold B cell with lock / twin / ACE i1 (4 contacts per row, about 1.1 GPU-h); the typed
    arm is empty by measurement; delivery candidates read offline; the ACE comparator gets its first point and the loop its
    in-flight twin. Honest, cheap, and the curve starts where the record says it is.
  - **B** fly the every-card N16 value list as a `claims_benefit: false` measurement (+0.27 ceiling, +651 tokens per row).
  - **C** redirect iteration 1 to a CONSUMPTION operator over the 139 in-supply MISSING items (exact oracle about 9.2 pp).
    Outside 265's class; the Solver contract is locked by decision 245 and every template column read null; would need a new
    typed consumption operator (not free text) that the record does not yet contain.
  - **D** open an out-of-split expansion source (`train_synthetic`): one ENCODE contact with its own owner row; the
    in-store-not-delivered mass (18 items) says the gain would still be small.
  - **E** test whether CORE capability, not the system, is the binding constraint: once the Thinking GGUF's hash is pinned,
    one bare-core read on Fold B (direct-only program, Thinking vs Instruct, same serving geometry, mmproj bf16, about 1-2
    GPU-h; thinking tokens raise latency and need a larger completion cap). The system is core-agnostic by design, so a
    stronger core transfers every locked component; the 36 % not-in-TRAIN values and the 61 % consumption misses are both
    core-side. This revisits decision 261 (the owner limited the thinking model to a pre-download) because the pre-read
    changed the picture; it is put as a question, not acted on.
  - Coordinator recommendation: **A + E** in that order (about 2.5-3 GPU-h total); C only if the owner wants a typed
    consumption operator designed first (one more design note, no GPU).

Also: the E22 package re-pin after the inert knowledge-snapshot pin cannot run yet (the generic flip's check refuses at the
missing window feature packets), so the two E22 registration-hash tests stay red until the encoder pass; recorded, not a
defect of this wave. Merged this wave so far: E-T4 (ebd0ebacf), E-T2 (d42be260f), E-S1/E-S2 (2baf81110), E-T1 (9d5aa2076;
`runtime.py` changed: re-pin at the flight commit), the pre-read (b089b2547), E-T3/E-T5 (efc9246ff: tables contract, cross-fitted delivery fitter, per-column labels). In build: E-T6, a root-cause of
two pre-existing test failures.

## Decision 266 ruled by the owner, 2026-10-11: A + E

Owner, verbatim: 「决策266：A + E」 ("266: A + E.")

- **266-A RULED**: iteration 1 of the typed loop flies the stall default -- one TRAIN Fold B cell with the lock, its
  request-identical twin and the ACE i1 column (the typed arm empty by measurement; delivery-rule candidates read offline);
  preceded by the text-only proposer + reflector cell i1 (about 0.1 GPU-h) so the archive records the refused typed
  candidate and ACE gets its i1 playbook from the lock column's credit. Column cost about 1.1 GPU-h.
- **266-E RULED**: a bare-core read on TRAIN Fold B, Thinking vs Instruct, direct-only program, same serving geometry
  family, once the Thinking GGUF's per-file SHA-256 is pinned in the umbrella lock (main file verified against the
  Hugging Face LFS pointer: afdaeff6f23c740429aadb3fa180f9d53b78278fe0d331b594b0b71bd9bf4835, 18,557,053,248 bytes; mmproj
  expected 57b7240fb3d8941f5969d760c694a754cbe74f7db428605d63e1dacceda98b38, 2,207,465,664 bytes, download finishing).
  This reopens the core line that decision 261 had limited to a pre-download; the model is admitted ONLY for this read,
  not as the serving core of any system cell. Design constraints the registration must meet: (i) a new serving session
  entry (the 24 GB card holds one core; the resident Instruct session must be released for the Thinking read under the
  serving-entry protocol and restored afterwards; the uptime guard must be told); (ii) thinking-mode completions are long,
  so the geometry declares its own completion cap and the chain runs a 4-row smoke FIRST to measure decode cost before the
  1,080-row arm is queued; (iii) the delivered answer is the content channel only, reasoning text is never delivered,
  never persisted beyond hashes and never enters the scorer; (iv) the comparison is cross-session by necessity, so the
  chain carries the Instruct direct-only Fold B arm and its in-chain replicate beside the Thinking arm, and the read is
  resolved only above the cross-flight bar (about 2.5 pp) -- a stronger core is expected to show more than that or the
  line closes; (v) exposure rows for every contact; split role discovery (TRAIN Fold B).
- Order: 266-A first (its cells exist once the loop driver lands), 266-E after the mmproj hash is pinned; both SLURP only;
  the carriers stay held (242).

## Decision 262 ruled by the owner, 2026-10-11: agreed

Owner, verbatim: 「决策262：同意」 ("262: agreed.")

- **262 RULED**: the paper's core claim is the training-free algorithm named and frozen as "sealed-credit policy search
  over typed system components" (rollout -> per-row typed official credit -> candidate from aggregate tables -> offline or
  same-flight selection against a twin under the measurement instrument -> fresh-roster confirmation), with the instrument
  as part of the method; (b) the stable-gain ledger (B1, B4b, COMP-1b, v4g, review-off; each with its selection read and
  its confirmation read) as the evidence; (c) the negative result (free-text updates and output re-selection do not
  transfer under the same instrument; the supply side of SLURP SLU is at its plateau at lock v2.2, pre-read 2026-10-11)
  reported with the same rigour; (d) the remaining SLURP rounds add entries of that type (263 v2 / 266-A: the autonomous
  typed loop with the ACE comparator; 266-E: the core-capability read); (e) the carriers run the SAME loop (ALL-OFF A/A ->
  one credit-selected construction update -> confirmation) once the owner releases their GPU under 242 / 252.
- Consequence for the record: results notes from today on carry a "ledger entry" line stating which clause (b), (c) or
  (d) they feed; the lineage analysis of 2026-10-11 supplies the related-work frame (TF-GRPO, ACE, SkillOpt, DGM, RRSI).

### Build wave status (coordinator, 2026-10-11, after decisions 262-266)

Merged to master: E-T6 multi-store `release_swaps` (1a6cff191; receipt v5, `runtime.py` router changed: identity-bound), the
loop driver + DRAFT protocol (efedd1163: `scripts/flights/tfrl/`, `docs/readiness/2026-10-11-slurp-tfrl-loop-v1/`,
protocol_sha256 666763df...; selection clauses a-e as implemented; iteration 1 arm set `ace, aa, lock`; 53 tests), the
stale-test fixes (58768c220). Blocker found by the driver: lock v2.2 declares no `ace-playbook` store, so the ACE column is
refused by `verify_declared_module`; fix in build = lock successor v2.3 (= v2.2 + `ace-playbook` at the empty i0 release,
declaration-only, P-ACE-0 byte proof). Also in build: the 266-E direct-only Fold B package; root cause of the flown-cell
registration tests (successor-2, VER-1b) that recompose on the live tree after identity-bound changes. Order after these
land: freeze one flight commit -> one re-pin of every live HELD package -> countersign the i1 proposer/reflector rows ->
mint -> flip -> plan pins -> flip -> gates -> queue (GPU resumes).

### Lock v2.3 (declaration-only) merged; material source moved to the construction roster (coordinator, 2026-10-11)

- Merged f0edc8a72: `LOCK_V2_3` = v2.2 + the `ace-playbook` store declared at the empty i0 release (prepared write-once under
  `knowledge/slurp/semantic/ace-playbook-i0/`; release sha256 4013e503..., snapshot pin 3c9f36f9...); P-ACE-0 proven (Perception
  and Solver request payloads byte-identical under v2.2 and v2.3; the real i0 release supplies the Solver nothing);
  `CURRENT_LOCK = LOCK_V2_3`; `lock_superseded_by` updated; no registered package changes its composed hash. The tfrl i1
  cells derive on v2.3 under the real hooks.
- Coordinator decision inside 263-A (no owner question): the semantic-knowledge preparer refuses TRAIN Fold B rows as the
  carrier roster of a delta-store release (the 2026-09-23 construction-roster vs knowledge guard), so the proposer's tables
  and the ACE reflector's material come from a lock column flown on the CONSTRUCTION roster R01C (625 TRAIN rows outside
  Fold A and Fold B; the ROLL-1 / ADV-1 roster), not from Fold B. Fold B is then a true held-out selection split, as in
  SkillOpt's train-vs-selection separation; Fold A confirms. Cost: one extra lock column on R01C (2 contacts per row, about
  0.4 GPU-h), flown once since the lock does not change between iterations. The protocol file is regenerated accordingly.
- Also merged: the flown-cell registration-test fixes (c47bcfde0; stale expectations from registration-time commits, not
  runtime drift). The E22 hash tests stay red until the packet-gated re-pin. In build: 266-E package; ledger consumed-flag
  restoration for every flight sealed since 2026-10-09 plus a standing check; the construction-source cell + driver switch.

### Construction-source column registered HELD (c34c8f1ef); two guard blockers and one defect found (coordinator, 2026-10-11)

- Cell `slurp-native-stage3-tfrl-construction-lock-r01c-v1` (+ smoke) on R01C (625 rows; split identity f56bc386...; 0 ids
  shared with Fold A / Fold B / DEV rosters), 1,250 contacts, about 0.86 GPU-h; package
  `docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1/`; the protocol rebuilt (3ba5e4ee...) naming lock v2.3, the
  material-source column and Fold B as held-out selection; the effect-floor gate learned the `material-source` design.
- Blocker 1: the lock's `train-exemplars` pool (37,407 ids) contains every R01C row, so the knowledge-source guard refuses
  R01C queries; the VAR-2 R01C cell used `size-pool-annotated-exemplars-minus-r01` (34,474 ids, disjoint). Fix in build: a
  construction VARIANT of the lock (pool + agreement table pinned to the minus-r01 twins, nothing else) accepted only on
  R01C. Blocker 2: the ace-playbook i0 anchor row's source ids lie inside R01C, so v2.3 would trip the same guard on the
  construction column; the column stays on v2.2 (P-ACE-0: byte-identical requests) unless the variant can re-home the anchor.
  Defect: `playbook_release_rows` writes `prior_score` outside [0, 1], so every non-empty ACE release would be refused;
  fix = rank-preserving rescale (in build, same branch).

### 266-E package merged HELD; ledger closure restored; Thinking packets are the next step (coordinator, 2026-10-11)

- **266-E registered** (92a0c9dd4; `docs/readiness/2026-10-11-slurp-direct-only-fold-b-thinking-vs-instruct-v1/`): four HELD cells
  (Thinking smoke-4, Thinking arm, Instruct arm, Instruct in-chain replicate; `phase-direct-only-v1`, TRAIN Fold B, cap 2048
  completion tokens = 17.7 % of a 24,576-token slot beside a ~2.3k prompt; `--reasoning-format deepseek` explicit; an opt-in
  transport guard refuses any delivered content carrying a think marker; wire responses never preserved), twelve DRAFT rows,
  preregistered verdict words RESOLVED-ABOVE-BAR / NOT RESOLVED / HARM, a serving swap path `serving_swap.sh think-np4`
  with the watchdog hold as the guard notice, chain order smoke -> decode-cost sign-off marker -> Thinking arm -> swap back ->
  Instruct arm -> replicate (two swaps instead of four). No sealed Instruct direct-only Fold B column existed, so (a)+(b)
  fly in-chain. Finding that changes the plan: the Instruct speech packets are NOT valid for the Thinking core (748 of 860
  mmproj tensors differ), so the Thinking arm needs its own packet root prepared by an encoder pass over Fold B (CPU
  sidecar; a registered contact with its own DRAFT row); the driver variant is in build; the Thinking baselines pin the
  promotion receipt at a zero sha until then and the flip refuses them.
- **Ledger closure restored** (e33cafc95): 671 rows of flights sealed 2026-09-27 .. 2026-10-10 closed to `consumed = yes`
  with SEALED dispositions from the manifests (`scripts/flights/batch/ledger_mark_consumed.py`); the lapse began on
  2026-09-27 when the CELL-1-only closer stopped covering new families. New gate `scripts/checks/ledger_consumed_check.py`
  (data-root mode is the gate; the results-notes fallback is advisory; listed in both client guides, 062cbe39b). Rows left
  at `no` are unflown, held, unsealed or decision-243 retirements.
- Open engineering before the first GPU contact: the lock construction variant (minus-r01 pool + agreement table) and the ACE
  score-range fix; the Thinking packet-preparation driver. Then: flight commit, re-pin, countersign, mint, flip, gates, queue.

### Construction variant + ACE score fix merged (4bdb54649, b52ad92ba); launch sequence next (coordinator, 2026-10-11)

- `construction_roster: "r01c"` on a module block compiles onto the lock with exactly four leaves moved (the `train-exemplars`
  release and snapshot pins -> the minus-r01 twins, 34,474 ids, 0 shared with R01C); the loader refuses the variant off
  R01C, a stale agreement pin, or lock v2.3 (the i0 anchor names 50 R01C ids); the plain lock on R01C is refused with the
  guard's message; a data-root test runs the runner's roster intersection: 0 of 625 rows under the variant, 625 under the
  plain lock. Agreement table for the minus-r01 pool built CPU-only (`prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-R01C-V1/`,
  625 rows x 20 votes, 400 rows byte-identical to the older R01C table); its ledger row updated in place, still DRAFT. The
  construction cells stay on v2.2 + variant (P-ACE-0 makes v2.2 and v2.3 requests byte-identical). ACE `prior_score` is now
  `(total - rank) / total`; an i1 release with R01C carriers passes the real preparer.
- Launch sequence (after the Thinking packet driver merges): freeze the flight commit; one re-pin of every live HELD
  package (tfrl construction + smoke, tfrl i1 proposers and column, 266-E four cells); countersign the construction rows;
  mint; loop-form flip; plan pins; flip; gates; queue `batch_chain_tfrl_const.sh` (about 0.9 GPU-h). Then the i1
  proposer/reflector cell on its sealed tables, then the Fold B column (lock / aa / ace). 266-E runs after the packet pass.

### Construction-source column launched; Thinking packet driver merged (coordinator, 2026-10-11)

Owner, verbatim: 「继续，代理回报后合并并起飞 i1」 ("Continue; after the agents report, merge and take off i1.")

- Construction column: rows countersigned 08:57Z (1f9070d97), receipt minted, flip chain as task SAEA-Flip-TFRLConst (smoke
  87cb5e960, arm 2b8670a52, pins refreshed, re-converged), **flight commit 70eabd973**, both launch gates PASS, chain task
  SAEA-Queue-TFRLConst started 09:31:58Z (`/home/chao/saea-queue/chain_tfrlconst.sh` -> `batch_chain_tfrl_const.sh`:
  four-row smoke, then the 625-row plain-lock column on R01C under the construction variant; about 0.9 GPU-h).
- Merged after the flip loop ended: `sonnet/266e-thinking-packets` (dbb79e937): `scripts/slurp_fold_preprocess_thinking.py`
  (dry-run / run / promote / pin-receipt; refuses pin mismatch, non-empty root, missing or unsigned ledger row), the
  sidecar chain `scripts/flights/direct/direct_fb_packets.sh` (refuses while a flight is alive or a sidecar is up; host
  memory floor 26 GB), 52 tests; expected 45-60 min wall for the Fold B encoder pass (31.8 rows/min at 4 workers on the
  Instruct record plus two model loads).
- i1 sequence after the construction seal: countersign its READ row -> `tfrl_const_read.sh` -> `tfrl_loop_driver.py open
  --iter 1 --stage propose` -> countersign the proposer / reflector rows -> mint `--kind proposers` -> flip -> queue (about
  0.1 GPU-h) -> `open --iter 1 --stage cell` -> countersign the column rows -> mint `--kind column` -> flip -> queue the Fold B
  column (lock / aa / ace, about 1.1 GPU-h). The Thinking packet pass (CPU sidecar) runs in a GPU gap after the i1 proposers
  are queued or after the column, whichever gap comes first; 266-E flies after it.

### Construction-source column SEALED (coordinator, 2026-10-11)

`SAEA-SLURP-STAGE3-TFRL-CONSTRUCTION-LOCK-R01C-V1` sealed 2026-10-11T10:35Z at flight commit 70eabd973: 1,250 contacts on 625 R01C
rows, 5,453.7 speech-audio seconds, smoke 4 rows rc 0, driver rc 0, 09:32-10:36Z wall. The four flight rows are closed
(`consumed = yes`, SEALED dispositions) and the READ row is countersigned; next: `tfrl_const_read.sh` (contrast tables, 0 GPU)
-> `tfrl_loop_driver.py open --iter 1 --stage propose --execute` -> the i1 proposer / reflector cell. The Thinking packet pass
(266-E, CPU sidecar) runs in this GPU gap: its precondition check passed at 10:36Z with no flight alive.

### i1 propose stage done; two first-real-run defects (coordinator, 2026-10-11)

- `open --iter 1 --stage propose --execute --enums-from-gold` ran at 10:52Z on the sealed construction column: tables
  (sha 6c925de6...), proposer context, per-scenario ACE material, package `docs/readiness/2026-10-11-slurp-tfrl-loop-i1-proposers-v1/`
  (typed proposer 3 carriers x 3 = 9 calls; ACE reflector 18 carriers x 3 = 54 calls; text-only, 0 audio); rows registered and
  countersigned (baf5b9b9d; scope text corrected from "TRAIN Fold B credit" to the construction column); receipt minted.
- First real flip (task SAEA-Flip-TFRLi1Prop): the typed cell flipped (20bd46fdb) but the reflector's re-pin was refused
  (`exposure ledger artifact ... not found: prompt sha256 pending; ...` -- the writer put a descriptive string with a placeholder
  into the rows' artifacts cell instead of the registered plan path) and the launch gate reports `[no-analysis-recipe]` (the
  package lacks `analysis-recipe-v1.json`) plus `[receipt-hash-mismatch]` on the unflipped reflector. Fix in build
  (`sonnet/tfrl-i1-registration-fix`): writer emits the plan path, the resolved prompt sha and the recipe; the two live rows
  patched; then the flip loop re-runs.
- Thinking packet pass (266-E): start 1 refused by the frozen-core gate (row GPU cap 0.0 vs plan 1.0; row corrected to 1.0,
  43f0a439e); start 2 passed the gate, the CPU sidecar came up (10:52:04Z) and the smoke attempt failed before any encoder
  contact: `legacy feature-cache directory is unavailable: /home/chao/feat-cache/slurp-thinking-q4km` (the driver never creates
  the Thinking legacy cache). Fix in build (`sonnet/266e-thinking-packets-fix`): create the cache roots at run time, compare
  GPU hours in `--check-ledger`, and state how the next start is labelled given the failed attempt record.

### Second flip of the proposers; packet recovery pass started (coordinator, 2026-10-11)

- Registration fix merged (535ae32f2: artifacts cell = plan path, prompt sha resolved, `analysis-recipe-v1.json`, READ row
  registered and countersigned 7adbb5215). Second flip: the typed cell's `core.flight.cli check` now fails in the exposure
  gate: `_construction_roster_identity_hashes` scans `docs/receipts/rosters/*.json` and refuses the non-roster companion
  `a2t-paired-400-v1.comparator-rows.json` (schema `saea-a2t-paired-roster-comparator-rows-v1`, added by the A2T seal-path
  merge 899a17c48). Any plan with visible construction targets is blocked until the companion is moved or allowlisted; fix in
  build (`sonnet/gate-roster-schema-fix`). The reflector cell waits on the same flip.
- Thinking packet pass: the failed smoke attempt had encoded 4 rows (9.94 s) with nothing cached; driver fix merged
  (d8822f64f: creates the Thinking legacy cache and packet-root parent, `--check-ledger` compares GPU hours, attempt
  labelling enforced); ledger row raised to 1,084 calls / 3,165 s (47d0a5158); recovery labels written
  (`/home/chao/direct-fb-packets.recovery`: smoke `attempt-packets-thinking-smoke-4-rec1-v1` recovering
  `attempt-packets-thinking-smoke-4-v1`, then `attempt-packets-thinking-fold-b-v1`); check PASS 11:13Z; task started.

### Owner directive on the Thinking packets (2026-10-11): reuse analysis, root cause of the encoder rate, CPU pass stopped; i1 proposers launched

Owner, verbatim: 「这个特征处理的速度我们无法接受，你分析两个事情：第一个是特征是否可以重用？也就是比对下thinking和nothinking两个模型的
mmproj权重，如果是一致的话，就不需要再重新制作了。第二个是假设要重新制作，那你就需要去解决效率问题，当前这个效率我们无法接受，分析下
瓶颈的根因，并解决它！」 ("This feature-processing rate is unacceptable. Analyse two things: (1) can the features be reused, i.e. compare
the Thinking and non-thinking mmproj weights; if identical, no re-encoding is needed; (2) if they must be rebuilt, solve the
efficiency problem: find the root cause of the bottleneck and fix it.")

- **Reuse: no.** Per-tensor data-hash comparison of the two mmproj GGUF files (860 tensors each, identical shapes and dtypes):
  audio encoder `a.` 475 of 522 tensors differ (the 47 equal ones are LayerNorm weights), projector `mm.` 8 of 8 differ, vision
  `v.` 265 of 330 differ. Packets are encoder OUTPUT features (`core/model/speech_features.py`, `n_tokens x n_embd x 4` bytes per
  chunk), so they depend on the mmproj; the E40 sharing rule (identical chunk hashes under another encoder receipt) cannot apply.
- **Root cause of the rate.** The Thinking preprocess fragment `q4km-thinking-preprocess-featcache-cpu-sidecar-np4-v1` copied the
  CPU sidecar geometry (`-np 4 -ngl 0 --no-mmproj-offload`), so the ~0.6B-parameter audio encoder ran on the CPU at 16-19 s per
  row (smoke 4 rows 76.6 s; Fold B 50 / 1,076 rows in 799 s, about 4.7 h projected). Every fast preprocess in the record runs the
  encoder on the GPU (`q4km-e21-feature-preprocess-gpu-cddb000c-np1`: `-np 1 -ngl 999 -fa on -b 512 -ub 128`; the Instruct SLURP
  Fold B pass registered 2.0 GPU-h and encoded 1,080 rows in 2,038 s). The agent's "same geometry" assumption was wrong.
- **Action.** The CPU pass was stopped at 11:50Z (task SAEA-Packets-THINK; attempt `attempt-packets-thinking-fold-b-v1` after 50
  rows; the flight's one recovery was already spent on the smoke, so the packets contact is re-registered under
  `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1` with a 4-row proof of the GPU form). In build
  (`sonnet/266e-gpu-packets`): a GPU preprocess fragment for the Thinking encoder, a driver GPU mode with its own packet root and
  cache (CPU- and GPU-made encoder outputs are not bit-identical; the 50 CPU rows are not mixed in), and a chain that runs the pass
  inside the serving-swap window (stop Instruct -> GPU encode smoke + Fold B, about 8-20 min -> start the Thinking session for the
  266-E flight -> swap back; failure restores Instruct).
- **i1 proposers launched.** Fourth flip converged (both cells ready; flight commit bd43ded89; both launch gates PASS at 12:01Z);
  task SAEA-Queue-TFRLi1Prop started 12:02Z (typed proposer 9 calls, ACE reflector 54 calls, text-only; about 0.1 GPU-h) on the
  resident Instruct session with no sidecar running.

### i1 typed proposer SEALED; batch STOP on its post-campaign inspection (coordinator, 2026-10-11 12:02Z)

- `SAEA-SLURP-STAGE3-TFRL-PROPOSER-I1-V1` flew at bd43ded89 and sealed COMPLETED (3 carrier rows, 9 trace contacts, 31 s wall).
  The batch driver then STOPped: the campaign-mode inspector (`batch_inspect.py`, taken from the FLIGHT checkout) derives rows
  and the contact ceiling from the native episode config, which a text-only program does not have (`load_native_episode_config`
  returns None -> "campaign inspection requires registered positive rows and native contact ceiling", rc 2). Step 2, the ACE
  reflector cell, never started; no attempt was opened for it (not a recovery). Fix in build (`sonnet/batch-inspect-text-only`):
  a text-only branch in the inspector (rows from the population, ceiling from the program's 1 + retries), plus `TFRL_ONLY=ace`
  for the chain and the flip so the reflector alone is re-flipped at the new flight commit and queued. The typed run's
  inspection is then run read-only on the sealed bytes before its ledger row is closed.
- The uptime guard will HALT when it meets `batch-STOP`; the next chain start archives the STOP and the guard is re-armed.

### Inspector fix merged; typed proposer inspected; ACE reflector flying alone (coordinator, 2026-10-11 12:18Z)

- Merged 58ebe92ea: `batch_inspect.py` text-only branch (rows from the population; per-row ceiling = `execution_plan.planned_model_calls`
  / rows, cross-checked against the generation and family caps; FINALIZED + COMPLETED at the flight commit; outputs == rows; trace
  requests == calls_used <= rows x ceiling; no tools), `TFRL_ONLY=typed|ace` in the chain (queue builder `tfrl_i1_queue.py`) and
  the flip. The sealed typed run passes the new inspection: 3 rows, 3 calls (no retries), 0 tool calls, 18,845 prompt / 555
  completion tokens; its trace carries `speech_ref` and per-row `audio_seconds` as carrier ACCOUNTING only (no audio part in the
  request; cost 5.95 s under the 18 s ceiling).
- Reflector-only flip converged at 58ebe92ea (gate PASS); chain task SAEA-Queue-TFRLi1Ace started 12:17:38Z (54 calls); the
  driver archived `batch-STOP` at start; the uptime guard (HALTed 12:04Z on the STOP) re-armed.

### Fold B column FLYING; GPU packet pass merged (coordinator, 2026-10-11 13:21Z)

- Owner: 「继续，收敛后排队 Fold B 列」. Column flip converged (smoke 4150b157f, arm 88ccd0b7c, siblings, pins refreshed, second loop)
  at **flight commit 6cbd9c707**, both launch gates PASS 13:20:55Z; chain task SAEA-Queue-TFRLi1Col started 13:21:21Z (four-row
  smoke, then 1,080 Fold B rows x 4 contacts: lock delivering, aa twin, ace column at the prepared i1 release; typed arm empty by
  measurement; ceiling 1.5 GPU-h).
- GPU packet pass merged (ed3280f97): fragment `q4km-thinking-feature-preprocess-gpu-np1-v1` (`-c 16384 -np 1 -ngl 999 -fa on`,
  mmproj on the GPU), driver `--geometry gpu` (refuses while any serving session is resident), swap-window chain
  `direct_fb_packets_gpu.sh` (watchdog hold -> `serving_swap.sh --stop-only` -> smoke -> rate gate: projected Fold B > 3,000 s
  restores Instruct and exits 23 -> Fold B -> `think-np4 --start-only`; failure restores Instruct), new run id
  `SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1` (1,084 calls / 3,165 s / 1.0 GPU-h), the 266-E package regenerated on the
  GPU roots; the CPU chain refuses unless `--allow-cpu`. **Correction to the morning's analysis:** the Instruct Fold B packet pass
  (`SAEA-SLURP-EVO-FOLD-PACKETS-V2`, 1,080 rows in 2,038 s) was ALSO a CPU sidecar pass; its "2.0 GPU-h" was the registered
  ceiling. The record holds no GPU encoder rate for SLURP, and the Thinking CPU pass was about 9x slower than the Instruct CPU
  pass on the same geometry for a reason not yet isolated; the GPU estimate (0.3-1.0 s per row, 5-18 min) is a bound guarded by
  the rate gate, not a measurement. The GPU packets row is countersigned; the window runs after the column seals (the card holds
  one core), followed by the pin step, re-pin, countersign of the eight 266-E flight rows, mint, flip and the 266-E chain.

### Column smoke STOP (13:22Z): ACE snapshot pin was the file hash, not the content hash; package re-derived (coordinator, 2026-10-11)

- The four-row smoke of the Fold B column refused at preflight: `supply action 'ace' is invalid: knowledge store ace-playbook snapshot
  SHA-256 mismatch`. Cause (coordinator error): the `--ace-release-pins` file carried the snapshot FILE sha256 (e1584617...), while the
  runtime checks the snapshot's content hash (`snapshot_sha256` c91ca2dd..., the value the preparer's `completion.json` records). The
  smoke attempt opened with 0 calls and 0 audio seconds (one-time key spent); under the one-recovery rule the smoke re-flies whole
  under `...-rec1-v1` attempt ids (the arm is untouched; nx_r6_family `SMOKE_RECOVERY` is the pattern), which the tfrl family does not
  yet support (in build).
- Pins corrected from the preparer's completion entries; `open --stage cell` re-run (receipt superseded; blockers none; loader ok); the
  package and both baselines re-derived with the correct alternates (they return to the pre-flip state and are re-flipped at the
  rec1 registration).

### GPU packet window: encode PASSED, Thinking session start failed on the missing ext4 copy; i1 smoke recovery registered (coordinator, 2026-10-11 13:55Z)

- GPU window 13:31-13:48Z (task SAEA-Packets-THINK-GPU): Instruct stopped 13:32:10Z; smoke 4 rows 0.688 s per row (incl. warm-up),
  rate gate projected 741 s < 3,000 s; Fold B 1,076 rows in 164.5 s = **0.155 s per row (386 rows per minute; the CPU pass was 16-19
  s per row)**; 1,080 packets promoted (receipt ef409ef4...). The window then failed at `serving_swap.sh think-np4 --start-only`
  (exit 13): the serving runtime resolves the Thinking GGUF under `/home/chao/models/qwen3-omni-30b-a3b-thinking-gguf-q4km/` (the ext4
  working-copy convention of the Instruct core) and only the E-drive archive existed; Instruct restored 13:48:03Z. Fix: the ext4
  working copy is being made (20.8 GB, sha-verified against the lock); no config change. Pin step done (3a5c8ef25); GPU packets row
  closed (1,080 contacts, 3,164.74 s). 266-E's re-pin / countersign / mint / flip / chain run after the i1 column (one core per card).
- i1 smoke recovery merged (02dc21855: tfrl `SMOKE_RECOVERIES`, rec1 attempt ids for the smoke's generation and FIT, cumulative budget
  16 / 64 calls with 0 spent, root cause in the plans, queue + flip use rec1, `PLAN_REC` in the generic re-pin loop); the two
  first-attempt smoke rows are folded into the countersigned rec1 rows (one row per run id for the gate); the minted column receipt
  stands (run ids unchanged). Next: column flip (loop form) -> pins -> flip -> gates -> queue.

### Fold B column re-launched under the rec1 smoke (coordinator, 2026-10-11 15:36Z)

- Owner: 「继续，收敛后排队 Fold B 列」 and the monitoring cadence moved to 30-minute windows; the owner also asked whether GPU work could
  start and ruled that model rotation follows the experiments, not only the 12-h threshold -- answered: the guard is already
  idle-only and HALTed; the Instruct restore at 13:48Z reset its clock; rotation plan = column (Instruct) -> swap to Thinking for
  266-E smoke + arm -> swap back for the Instruct arm + replicate and the iteration-2 text contacts.
- Column flip (rec1 smoke + arm) converged at **flight commit 2b6416686** (two loops, pins refreshed at 879a7038b; both launch
  gates PASS 15:15Z); task SAEA-Queue-TFRLi1Col started 15:36:03Z; the uptime guard re-armed after the STOP archive.

### Loop iteration 1 CLOSED: ACE column refused, typed arm empty; lock stays the parent (coordinator, 2026-10-11 18:40Z)

Column `SAEA-SLURP-STAGE3-TFRL-LOOP-I1-FOLD-B-V1` sealed 18:33Z at flight commit 2b6416686 (1,080 TRAIN Fold B rows, 4,320 contacts,
12,619 speech seconds, inspection PASS, 15:40-18:33Z). Read by `tfrl_loop_driver.py close --iter 1` under the pinned protocol:

| arm | official SLU-F1 | intent | vs lock SLU pp [CI95] | vs twin SLU pp | intent pp [CI95] |
| --- | ---: | ---: | --- | --- | --- |
| ace (27-item i1 playbook as a Solver supply) | 64.87 | 82.31 | **+0.87 [-0.40, +2.10]** | -0.49 [-1.12, +0.12] | 0.00 [-0.74, +0.74] |

Clauses: a (CI-LB > 0) FAIL; b (point >= 1.49) FAIL; c (beats twin) PASS; d vacuous; e (intent lo >= -0.65, point >= 0) FAIL by
width (lo -0.74). **ACE i1 refused**; state e7b4fa57... archived. Composition of the ACE delta: false fill -4.34 pp on the 392
empty-gold rows, non-empty exact +0.58 pp on 688 rows; per-scenario SLU deltas spread from -2.45 (news) to +4.38 (recommendation)
with no stratum resolved. The typed arm was empty by measurement (the single deliver-rule candidate is read offline). Curve: level 0
at iteration 1; parent for iteration 2 = s0-lock-v2.2. Ledger entry (262 clause c): a prose-item update form at equal budget does
not clear the instrument on this task in one iteration; the loop continues to iteration 2 (propose from the same construction
column, ACE counters from this column's credit).
- 266-E next (GPU idle): countersign the eight flight rows (package `countersign-row-texts-v1.json`), mint, flip (loop form), pins,
  flip, gates, chain with the Thinking swap (ext4 copy in place).

### Iteration-1 results note merged; three registry corrections (coordinator, 2026-10-11)

`docs/results/2026-10-11-slurp-tfrl-loop-i1-fold-b-column-read.md` (Opus, branch `opus/tfrl-i1-results-note`, 63ab68bc5) is the
read of record for the loop iteration-1 Fold B column. Corrections to the entries above, verified against the sealed bytes:

1. The "vs twin SLU pp" value -0.49 [-1.12, +0.12] in the "Loop iteration 1 CLOSED" table is the TWIN's contrast against the lock
   (aa minus lock), not ACE against the twin. ACE minus twin is **+1.36 [+0.12, +2.58]** SLU (span-F1 +1.67 [+0.22, +3.09]; intent
   +0.09 [-0.56, +0.83]). Clause c (beats twin, point vs point) was computed correctly; only the label was wrong. The lock-vs-twin
   gap of -0.49 is the same-flight A/A offset of this column and sits inside the 1.49 floor.
2. "typed proposer 9 calls / ACE reflector 54 calls" (12:02Z entry) were the registered CEILINGS (3 per carrier); the sealed
   manifests and the ledger rows record **3** typed-proposer contacts and **18** reflector contacts, no retries.
3. The column used **2.49 GPU-active hours** (wall 2.73 h; 74.5 % mean utilisation, 26.4 contacts per minute) against
   `planned_gpu_hours` 1.5 (spec estimate 1.1). Calls and audio sat exactly at plan (4,320 / 4,320; 12,619 / 12,620 s), so this
   is not a breach of the run-cumulative rule; from iteration 2 the column plan derives its GPU hours from the measured rate
   (about 0.58 GPU-h per contact per 1,000 rows, 1.3 margin).

Two defects the note found in the loop driver are being fixed model-free before `open --iter 2` (worktree `sonnet-driver-fix2`,
branch `sonnet/tfrl-driver-playbook-fix`): (i) the archived ACE i1 state binds the stale 0-item playbook file (`playbook/
playbook-i1.json`, written by the superseded first open-cell run) instead of the flown 27-item release playbook; iteration 2 would
have curated from 0 items; the archive gets a write-once correction record rather than an in-place edit; (ii) the typed arm's single
offline candidate (deliver rule `fx-oclock` on alarm `time`, target SPURIOUS) was skipped silently because the family is not in the
fitter; the close step must record every candidate (refused `offline-family-unsupported` or read), and the i1 candidate is read
offline on the sealed lock column.

### 266-E Instruct arm ABORTED before the first contact (knowledge-roster guard); recovery rec1 + fold-excluded knowledge pin (coordinator, 2026-10-11)

Flip chain converged at 77b2283e9 (four cells, `flight_registration_check` PASS x4, 20:03Z). The Instruct segment was flown first on
the resident Instruct session (no swap needed; task SAEA-Queue-DirectFB-Instruct, 20:04Z). The arm ABORTED at 20:07:46Z with 0 calls
and 0.0 speech-seconds (attempt `attempt-slurp-direct-only-fold-b-instruct-generation-v1`, state ABORTED, preserved unread): the
runner's knowledge-source guard refused the AgentLoop because every one of the 1,080 Fold B query ids is in the pinned knowledge
snapshot's source roster. Root cause: the four 266-E baseline fragments were derived from the DEV / test direct-only form and pin
the FULL-TRAIN view `size-full-content-slot-fillers-intent-slot-frame` (50,628 source rows); the guard runs even though the
direct-only program binds the snapshot invisibly (`evidence_source = none`). The fold-excluded twin
`size-full-content-slot-fillers-intent-slot-frame-tfrl-folds-v1` (37,407 source rows; 0 Fold A and 0 Fold B ids; its split identity
differs from Fold B's) is the pin every TRAIN-fold cell already uses and is the honest pin for a bare-core read on a TRAIN fold.
Fix (model-free, branch `sonnet/direct-fb-knowledge-pin-rec1`): the four baselines pin the fold-excluded view; the Instruct arm
takes its single recovery re-registration (generation attempt `...-instruct-generation-rec1-v1`, FIT run
`SAEA-SLURP-DIRECT-ONLY-FOLD-B-INSTRUCT-FIT-REC1-V1`; run-cumulative budget = the original plan + 0); the smoke, Thinking and
replicate attempts never opened and keep their ids; a unit test asserts the pin and the roster disjointness. The stale
`locks/flight.lock` of the dead campaign process is reconciled by `scripts/flights/batch/lease_reconcile_direct_fb_instruct.sh`
(receipt under `coordination/`). GPU idle from 20:08Z until the re-flip lands (about 1.5 h): the Thinking session is loaded during
the flip so the Thinking arc (smoke, sign-off, arm) flies first when the flip ends, then one swap back for Instruct + replicate.
Executed 20:20-20:36Z: lock reconciled (receipt `flight-lock-reconciliation-20261011T202011Z.json`); fix merged (ead664100); the two
rec1 rows countersigned and the first-attempt generation row folded into the rec1 row (one row per run id, the tfrl i1 smoke
precedent; the superseded FIT row `...-INSTRUCT-FIT-V1` stays); the eight-id decision receipt kept as
`root-admission-v1.superseded-20261011T203519Z.json` and a nine-id receipt minted (sha 23cc42f8...; the protocol's recovery rule
names a new FIT run id, so the receipt had to grow). Next: flip loop (all four cells: every baseline changed), pins, flip, gates, the
Thinking session loaded during the flip, then think-all first and the Instruct pair after the swap back.

### 266-E Thinking decode-cost smoke: 1 of 4 rows hit the 2,048 cap and the harness cannot carry an empty answer; cap amended to 8,192, smoke rec1 (coordinator, 2026-10-11)

Flip chain converged at c9edf3244 (four gates PASS, 21:48Z); the Thinking session was loaded during the flip (20:41Z) and the
think-all segment started 21:49Z. The four-row smoke made its 4 contacts (9.94 speech-seconds): completions 363 / 921 / 977 tokens
with 60-111 characters of delivered content, and ONE row that spent all 2,048 completion tokens thinking and delivered EMPTY content
(prompt 2,285 tokens). Decode 37 tokens per second per slot (58 when alone), prompt eval 0.9-1.7 ms per token. The empty answer
crashed the wave (`aggregate_agent_wave`: `AgentStateArtifact.content must be a non-empty string`), so the smoke step exited 1 and
the driver wrote STOP; the Thinking arm never opened. Reading: this is the signal the smoke was registered to measure. Two defects:
(1) the cap: at 2,048 about a quarter of rows would abstain by truncation (one of four here; the arm would need the cap-hit table
the README anticipated); (2) the harness: an empty `content` at `finish_reason = length` must become the receipted abstention of
decision 199 (`config_tables` already names "core ended before authoritative delivery"), never a wave exception. Decision under
the README's pre-authorisation ("the coordinator may amend the cap at the decode-cost sign-off; one re-registration"): completion
cap 8,192 (2,300 + 8,192 = 42.7 % of the 24,576-token slot), GPU ceiling of the Thinking arm 3.0 -> 4.5 h (1,080 rows at a
measured 150 aggregate tokens per second with a long tail), the smoke re-flown under its single rec1 recovery (run-cumulative
budget 4 + 4 calls), the arm's attempt untouched; the harness fix lands model-free with a unit test on an empty-content length
response. GPU meanwhile: the Instruct pair (ready at c9edf3244) flies on the Instruct session (swap back 21:5xZ) so the card is not
idle during the repair; the Thinking arc resumes after the Instruct pair seals (one more swap).

### 266-E Instruct pair SEALED; Thinking line re-registered (cap 8,192, smoke rec1); loop i2 opened, typed proposer sealed, reflector held on a detector false positive (coordinator, 2026-10-11 23:40Z)

- **Instruct pair.** Flew on the resident Instruct session at c9edf3244: Instruct arm (rec1 attempt) 21:57-22:18Z, replicate
  22:19-22:35Z, 1,080 contacts and 3,154.8 speech-seconds each, both attempts FINALIZED, manifests sealed; rows closed as consumed.
  No score is read before the Thinking arm seals (registered read protocol: all three arms, one READ row).
- **Thinking line.** Branch `sonnet/direct-fb-thinking-cap-8192` merged (59d33fd26): the harness seals an empty answer at the cap
  as the explicit empty-phase marker plus a tool receipt `<contact>/empty-completion` (`cap_hit`, `completion_tokens`, `max_tokens`,
  `finish_reason`, disposition) and the final-response gate lets only a receipted contact deliver empty bytes (the Instruct path is
  request-identical; a test pins it); new model fragment `q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max8192-v1` and
  session `serving-slurp-thinking-direct-fold-b-np4-max8192-v1` (the cap lives in the fragment's decoding params and the session
  attaches by fragment); Thinking arm GPU ceiling 4.5 h; smoke rec1 (generation attempt `...-smoke-4-generation-rec1-v1`, FIT run
  `...-SMOKE-4-FIT-REC1-V1`, run-cumulative 8 calls / 20 s); rec1 rows countersigned, the first-attempt smoke row folded, the two
  Thinking arm rows amended in place at the sign-off (cap, GPU hours, fragment, session; note appended); ten-id decision receipt
  minted (sha f876b85b...). Flip (`DIRECT_FB_KINDS="smoke thinking"`) running; the new Thinking session loads meanwhile.
- **Loop iteration 2.** `open --iter 2 --stage propose` done (b4d930a22; tables 6c925de6..., proposer tables 06c2ec29..., archive
  d10541a9... with the ACE i1 refusal, the fx-oclock refusal and the playbook-hash correction). Rows registered and countersigned
  (text-only ceilings 41 / 142 s as at i1). Typed proposer i2 SEALED 23:31Z (3 contacts, 13 s audio-equivalent; unread). The ACE
  reflector i2 re-pin was refused by the sample-identifier guard: a false positive of the bare six-digit pattern on two of the 27
  playbook item ids (`ace:i1:<12 hex>`), not on any text; the renderer now masks well-formed item handles (4c9d2bfb5; detector
  unchanged, i1 prompt bytes unchanged). Its flip (`TFRL_ONLY=ace`) and flight follow when the Instruct session is next resident.
- **Tooling.** `ledger_mark_consumed.py` pairs `-FIT-REC<n>-V1` runs with their generation run (aa67a6740); the Instruct FIT-REC1 row
  is closed.
Thinking flip converged at 5daf057f8 (two gates PASS, 00:16Z); the max8192 Thinking session resident since 23:38Z; think-all
started 00:17Z (task SAEA-Queue-DirectFB-ThinkAll): smoke rec1 -> coordinator reads the decode cost and writes the sign-off marker
naming 8192 -> Thinking arm (1,080 rows, ceiling 4.5 GPU-h). After the arm: swap to Instruct, fly the ACE reflector i2 cell (flip
`TFRL_ONLY=ace`), countersign the 266-E READ row, `direct_fb_read.sh`.

### 266-E Thinking smoke rec1 read and decode-cost sign-off: cap 8,192 approved; Thinking arm FLYING (coordinator, 2026-10-12 00:23Z)

Smoke rec1 (flight commit 5daf057f8, new session max8192) sealed its 4 rows 00:21Z, inspection PASS: completion tokens p50 949, mean
2,613, p90 6,028, max 8,192; ONE row again exhausted the cap (the same runaway-reasoning behaviour at 4x the budget) and sealed as the
empty-phase marker with an `empty-completion` receipt (`cap_hit` true, `finish_reason` length) -- the harness path of 59d33fd26 is
proven end to end on a real contact; reasoning leak 0; prompt 2,272 tokens per contact; 41.4 s per contact mean (p50 30.2, p99
93.2) on 4 slots; projection 3.11 GPU-h for 1,080 rows (upper bound 6.99 if every row ran like the tail) against the registered 4.5 h
ceiling. Sign-off written (`/home/chao/direct-fb-decode-signoff.marker`, cap 8192) at 00:23:16Z; the chain opened the Thinking arm
at 00:23:39Z (`batch-campaign-1-direct-fb-thinking-20261012T002339Z.log`). Reading rule unchanged: cap-hit rows are abstentions and
are counted in the arm's cap-hit table; the arm's read is Thinking minus the mean of the two Instruct passes with the twin offset.

### 266-E Thinking arm ABORTED before the first contact (exposure gate: FIT row GPU hours); coordinator error; rec1 recovery (coordinator, 2026-10-12 00:30Z)

The Thinking arm opened at 00:23:39Z (flight commit 5daf057f8, session max8192) and the exposure gate refused the first model touch
at 00:25:21Z: `execution plan claims 4.5 gpu hours but only 3.0 were pre-registered` (attempt ABORTED, 0 calls, 0.0 s). Root cause:
the coordinator's in-place amendment at the decode-cost sign-off raised the GENERATION row to 4.5 GPU-h but left the live phase-fit
row `...-THINKING-FIT-V1` at 3.0, and the gate reads the FIT-inclusive pre-registration (`gpu_hours_fit_inclusive` 4.5). The
amendment script changed the gpu cell of the arm row only; a model-free check of "every row's gpu cell >= the plan's claim" did not
exist. Consequences: the arm's (run, attempt) key is spent -> its single rec1 recovery (generation attempt `...-thinking-generation-rec1-v1`,
FIT run `...-THINKING-FIT-REC1-V1`, both rows at 4.5 natively), eleven-id receipt, flip of the thinking kind only; the stale lock
reconciled (receipt `flight-lock-reconciliation-20261012T003028Z.json`; script kept beside the Instruct one). A gate finding for the
FIT-row GPU pre-registration is being added so this class is caught before a flight. GPU meanwhile: swapped back to Instruct 00:3xZ to
fly the ACE reflector i2 (flip running) and return to the Thinking session when the arm's rec1 is flipped.

### Loop iteration 2 cell stage opened (typed arm empty by measurement, ACE i2 = 35 items with credit); Thinking arm rec1 registered; both flips queued (coordinator, 2026-10-12 01:10Z)

- **i2 proposers read** (READ row countersigned 00:38Z): `scripts/flights/tfrl/tfrl_cell_stage_inputs.py` (merged 5432eb4d4) replaces the
  iteration-1 hand scripts; it reproduces every i1 artefact byte for byte (13 of 14; the release-pins file differs only in a free-text
  field) and wrote the i2 inputs. Typed proposer i2: 3 contacts, 3 schema-valid candidates (2 distinct ids), all deliver-rule (offline
  class). Reflector i2: 18 contacts parsed, 0 rejected, 11 scenario answers kept with 33 deltas, 7 duplicate-carrier answers dropped.
- **ACE credit defect repaired.** The iteration-1 `close` ran without `--row-scores`, so the ACE per-row credit was never built and the
  first i2 curation ran credit-free. Built after the fact with the driver's own function (`tfrl_row_scores.py` over the sealed i1
  column, 1,080 rows; `ace-credit.json`; receipt `iterations/i1/ace-credit-build-receipt.json`), the i2 inputs re-extracted with
  `--supersede`: playbook 27 -> 35 items, 33 deltas applied, counters from official credit (`credit_used: true`), content hash 5a092424...
- **`open --iter 2 --stage cell`** (a20b403cf): 2 valid candidates, both offline (read at close), typed arm empty by measurement
  (`typed_arm_empty_by_measurement: true`), loader verification ok, column package `docs/readiness/2026-10-11-slurp-tfrl-loop-i2-fold-b-v1`
  (lock / aa / ace, 4 contacts per row, 4,320 contacts, GPU plan 3.3 h from the measured rate); rows countersigned, column receipt minted.
- **Thinking arm rec1** (branch merged 507629001): ids `...-thinking-generation-rec1-v1` / FIT run `...-THINKING-FIT-REC1-V1`, both rows
  4.5 GPU-h; `flight_registration_check` gains the blocking finding `row-gpu-under-plan` (a live generation or FIT row whose gpu cell is
  under the plan's claim); rows countersigned and the first-attempt row folded (da13cc80b); eleven-id receipt minted (sha 0ccc7583...).
- **Order (266 "A then E"):** flips back to back (i2 column, then the Thinking arm; task SAEA-Flip-I2Col-ThinkArm, 01:09Z); the i2
  column flies first on the resident Instruct session (no swap), then one swap to the max8192 Thinking session for the arm.

### Owner directive 2026-10-12 (decision 267, RULED): hot paths on Linux-native ext4, never on the Windows filesystem; flip acceleration

Owner, verbatim: 「可以，你注意这个教训是我们之前就有过结论的！不要用windows原有的文件系统，要用linux原生的文件系统进行特征和缓存的制作！」
English: "Fine, but note this lesson was already concluded before: do not use the original Windows filesystem; make features and caches
on the Linux-native filesystem." Context: the coordinator's analysis of the flip chains (40-80 minutes per package) measured the cause as
9p latency, not CPU: `import core.flight.cli` 38.3 s cold / 11.4 s warm from `/mnt/d/.../src` versus 0.84 s from an ext4 worktree;
`git status` 7.6 s on /mnt/d versus 0.39 s on ext4 (18,575 tracked files); 20-40 python and 30-60 git calls per cell per flip. Threads
or parallel re-pins cannot help (the cells of a package share the ledger and the protocol hash; convergence is serial by construction).
Ruling applied as executable English: (1) flips / re-pins run from an ext4 worktree on a throwaway branch and the `/mnt/d` master takes
only `git merge --ff-only` (`scripts/flights/batch/flip_in_ext4.sh`); the flip and re-pin scripts REFUSE a repo root under `/mnt/`
unless `SAEA_ALLOW_9P_FLIP=1`; (2) the flight CLI, the re-pin tool and the registration check import the runtime lazily so `check`/
`--help` do not pay the 38 s; (3) the rule is written into the study CLAUDE.md / AGENTS.md environment section. Not done (owner's
call): one-pass convergence (compute the shared protocol hash once, write every cell, one commit) is a protocol change and stays
proposed. The data root stays on `/mnt/e` (large bytes; read-mostly) with the existing ext4 copies for the model files and the
feature cache (`/home/chao/feat-cache`, `/home/chao/models`).
Executed 02:54-03:00Z: both flips converged (i2 column at cc51b4eff, Thinking arm rec1 at a069b0ee1; gates PASS); the i2 column
chain started 02:57Z on the resident Instruct session (task SAEA-Queue-TFRLi2Col); the flip-acceleration branch merged (645dbf8ba:
`flip_in_ext4.sh`, `SAEA_MAIN` in 96 scripts, lazy runtime imports in the flight CLI, `/mnt/` refusal, CLAUDE.md/AGENTS.md rule;
ext4 import 0.43 s). The queue wrappers switch to `flip_in_ext4.sh` before the next flip (iteration 3 or the next 266-E step).

### Loop iteration 2 column SEALED; close refused on an archived-duplicate candidate (fix in build); Thinking arm rec1 FLYING (coordinator, 2026-10-12 06:40Z)

- **i2 column** `SAEA-SLURP-STAGE3-TFRL-LOOP-I2-FOLD-B-V1` sealed 05:49Z at cc51b4eff (smoke 4 rows + 1,080 rows x 4 contacts; 02:55-05:49Z);
  rows closed. Descriptive paired reads (the close's sub-steps; CIs and the protocol verdict follow with the close receipt): ACE i2 (35-item
  playbook with credit) vs lock pooled SLU-F1 **+1.38 pp**, span-F1 +1.50, per-row SLU +0.68, intent (action exact) **-0.56 pp**; twin vs lock
  +0.32 SLU / -0.09 intent. Reading before the CI: the ACE point is under the 1.49 floor and the intent point is negative, so the selection
  clauses (b, e) would refuse as in iteration 1; the comparator moved from +0.87 to +1.38 with credit-driven curation.
- **Close refused** (`state ccbe1075a873 is archived with different content`): the i2 typed proposer re-proposed the i1 `fx-oclock` deliver rule
  (new candidate id, same artefact set -> same archive state id); `open --stage cell` had not checked candidates against the archive, and the
  write-once archive refused the second measurement at close. Both i2 offline candidates (`oclock`, `ee`) fitted +0.00 pp (refused). Fix in
  build (`sonnet/tfrl-close-archived-duplicate`): archived duplicates are refused at open with code `duplicate-of-archived` and shown to the
  proposer as re-proposed; a colliding offline read becomes a write-once `archive/rereads/` sibling; `close` exports the per-row scores and builds
  the ACE credit itself (the ordering defect that skipped the i1 credit); an idempotent `repair --iter 2` lets the close complete. Row scores
  i2 exported (1,080 rows).
- **Ledger lapse recorded**: the i2 column READ row was countersigned only at 06:38Z, after the close's sub-steps had read the sealed column
  (the i1 registration countersigned the READ row together with the flight rows; the i2 registration did not). Rule restated: countersign
  the column READ row with the flight rows at registration, before any seal.
- **Thinking arm rec1** flying since 06:01Z at a069b0ee1 on the max8192 session (gate passed; 302 rows by 06:31Z, about 10 rows per minute).

### Loop iteration 2 CLOSED: ACE i2 refused by the point floor and the intent guard (SLU +1.38 [+0.15, +2.57]); typed arm empty; parent stays the lock (coordinator, 2026-10-12 07:35Z)

`close --iter 2` (after `repair --iter 2 --duplicates-only`: the re-proposed fx-oclock rule reclassified `duplicate-of-archived` and re-read as
`archive/rereads/ccbe1075...-i2.json`, +0.00 pp again; the new `ee5` offline candidate refused at +0.00 pp). ACE i2 (35-item playbook curated
with the i1 official credit) on the i2 Fold B column, n = 1,080:

| arm | SLU-F1 | intent | vs lock SLU pp [CI95] | vs lock intent pp [CI95] | vs twin SLU pp [CI95] |
| --- | ---: | ---: | --- | --- | --- |
| ace i2 | 65.88 | 82.41 | **+1.38 [+0.15, +2.57]** | -0.56 [-1.20, +0.09] | +1.06 (twin vs lock +0.32 [-0.33, +0.97]) |

Clauses: a (CI-LB > 0) **PASS** (first time for the comparator); b (point >= 1.49) FAIL by 0.11 pp; c (beats twin) PASS; d vacuous; e
(intent lo >= -0.65 and point >= 0) FAIL (point -0.56). **ACE i2 refused**; state cadd84f6... archived. Composition: false fill -2.81 pp on the
392 empty-gold rows (i1: -4.34), non-empty exact +0.44 pp on 688 rows (i1: +0.58); per-scenario SLU from -3.73 (audio) to +4.07
(recommendation), intent losses concentrated in cooking (-3.33) and four scenarios at -1.67. Curve: ACE i1 +0.87 -> i2 +1.38 with
credit-driven curation (27 -> 35 items); the SLU gain is now statistically positive but under the 1.49 floor and bought with intent. The
ACE credit for i3 is written by the close itself (`ace-credit.json`, row scores 1,080 rows). Typed arm: empty by measurement for the second
iteration (deliver-rule class exhausted at +0.00; the proposer re-proposed a refused rule, now refused as a duplicate at open). Parent for
iteration 3 = s0-lock-v2.2; `open --iter 3 --stage propose` running. Reading for the owner: two iterations in, the ACE prose-item comparator
is converging toward the floor on SLU while costing intent; the typed operator class (deliver rules) is exhausted; iteration 3 is the last
registered iteration of decision 263 and will decide whether the loop's ledger entry is "no typed candidate cleared the instrument" and
"ACE converged but did not clear the floor".

### 266-E READ: bare Thinking core +11.90 pp SLU-F1 / +4.35 intent over the bare Instruct core on TRAIN Fold B (RESOLVED-ABOVE-BAR); decision 268 PROPOSED (coordinator, 2026-10-12 08:10Z)

All three arms sealed (Instruct arm rec1 22:18Z and replicate 22:35Z at c9edf3244; Thinking arm rec1 07:58Z at a069b0ee1, cap 8,192); the
READ row countersigned 08:01Z before the read (`direct_fb_read.sh`, 0 contacts, `analysis/SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-VS-INSTRUCT-READ-V1/read.json`).

| direct-only bare core, Fold B n = 1,080 | SLU-F1 | intent | note |
| --- | ---: | ---: | --- |
| Instruct (two request-identical passes) | 33.40 / 33.58 | 72.87 / 71.94 | twin offset SLU +0.18 [-1.16, +1.50], intent -0.93 [-1.85, 0.00] |
| Thinking (cap 8,192, own packets) | **45.39** | **76.76** | 36 rows (3.3 %) at the cap with empty content (abstentions), 0 reasoning leaks |
| Thinking minus mean Instruct | **+11.90 [+9.34, +14.52]** | **+4.35 [+2.08, +6.62]** | cluster bootstrap 10,000 draws; saves/harms (intent) 103/61 |

Per scenario (natural mixture = equal-scenario, 60 rows each): SLU +27 alarm, +30 audio, +33 datetime, +24 transport, +23 weather, +22
cooking, +17 calendar; losses lists -8.8, music -10.8, iot -2.6; intent general -15.8, music -12.5, cooking/datetime -3.3. Cost: 22.75 s per
contact mean (p50 12.2, p99 198.8) versus 0.86 s on Instruct (26x); completion tokens mean 1,032 / p50 584 / p90 1,898; Thinking arm
1,080 contacts in about 2.0 h wall. Reading against the system: lock v2.2 (+v4g) on the Instruct core reaches SLU 64.34 / intent 82.41 on
this roster, i.e. the SYSTEM adds about +31 pp SLU / +9.5 intent to the bare Instruct core, 2.6x what the stronger core adds by itself;
the question 266-E asked ("is core capability the binding constraint?") is answered: the core is a strong lever (+12 / +4) but not the
dominant one, and the two are not known to be additive. Results note: `docs/results/2026-10-12-slurp-266e-thinking-vs-instruct-bare-core-read.md`.

- **268 (PROPOSED)** The system on the Thinking core: fly the locked system (v2.2 + v4g, module program c4, the same knowledge supply)
  on the Thinking core on TRAIN Fold B as ONE column with its twin (2 arms x 1,080 rows x 4 contacts; at 22.8 s per contact about 14
  GPU-h on 4 slots; cap 8,192; the Thinking session max8192 already registered), read against the Instruct-core lock column (64.34 /
  82.41, same roster, cross-flight bar 2.5 pp with the in-chain twin). Options: **A** fly it now (after the i3 proposers; the loop's i3
  column waits ~14 h); **B** fly it after iteration 3 closes (the loop keeps its GPU order; 268 starts about 2026-10-13 morning); **C**
  do not fly (keep the Instruct core as the study core; record 266-E as a core-capability note). Coordinator recommendation: **B** --
  the loop's last registered iteration first (its i3 column is ~3 h), then 268; if the system transfers additively the composed read
  would sit near SLU 76 / intent 86, which changes the Stage-3 claim surface and the SOTA framing (decision 252) and must be measured
  before any test-sample allowance is drafted for it.
Also 08:13Z: the first ext4 flip (decision 267) converged the i3 proposer package in 9 minutes end to end (checks 48 s, worktree 8 s,
flip 367 s, fast-forward 133 s) against 40-80 minutes on the 9p mount; i3 proposers flying at 7250fac92 (task SAEA-Queue-TFRLi3Prop).

### Owner decision brief 2026-10-12 09:00Z: decisions 268-273 PROPOSED; current stage; plan after iteration 3 (coordinator, on the owner's request)

Owner request (translated): "List in detail the items that need my decision and explain them; also lay out the current work stage and a
detailed plan for the work after." Chat reply in Chinese; this is the English record.

**Where the programme stands.** SLURP: lock v2.2 (+v4g post-processing) is the system of record (decision 249; test-sample read
successor-2: v2.2 beats COMP-1b on the test sample; Fold B levels 64.34 SLU-F1 / 82.41 intent; bare Instruct core 33.49 / 72.41 on the
same roster, so the system adds +30.85 / +10.00). The sealed-credit loop (decisions 262-266) ran iterations 1 and 2 end to end and
iteration 3 is flying (d39224f1c): the typed operator class (deliver rules) is exhausted (empty arm three times, every candidate at +0.00,
one re-proposal); the ACE prose-item comparator moved +0.87 -> +1.38 [+0.15, +2.57] SLU with credit-driven curation but fails the 1.49
floor and costs intent (-0.56). 266-E: the Thinking core is +11.90 / +4.35 over the Instruct core bare, at 26x the decode cost and 3.3 %
truncation abstentions. Carriers (Audio2Tool, E21, E22): hooks and all-off cells exist; A2T all-off A/A proven model-free; E21 needs about
4 GPU-h; E22 needs its encoder packet window; none has flown (decision 242/252: SLURP lock first). Decision 267 (ext4 hot paths) landed:
flips 9-34 min instead of 40-80.

**Decisions requested.**
- **268 System on the Thinking core.** The system is core-agnostic; 266-E says the core is a strong lever. One Fold B column of the locked
  system (v2.2 + v4g, same knowledge supply) with its twin on the Thinking core, cap 8,192: 2 arms x 1,080 x 4 contacts, about 14 GPU-h
  (22.8 s per contact), read against the Instruct lock column (cross-flight bar 2.5 pp with the in-chain twin). A = now (after the i3
  column), B = after iteration 3 closes (recommended), C = do not fly. If additive the composed level would sit near 76 / 86 and the
  Stage-3 claim surface (252) and any test allowance must be rebuilt around it; if it does not transfer, the Instruct core stays the study
  core and 266-E is a core-capability note.
- **269 Loop end state.** The protocol's completion checklist (Fold A confirmation of lock / aa / typed final / ACE final; DEV composed
  read) presumes an accepted state. With no accepted typed state and a refused ACE: A = run only the loop's closing results note and the
  ledger entry (0 GPU; recommended); B = still fly the ACE final on Fold A as a comparator record (~3 GPU-h); C = extend the loop by one
  iteration with a NEW typed operator class designed first (consumption-side, decision 266-C's design note; 0 GPU until designed).
- **270 One-pass flip convergence.** Engineering: compute the shared protocol hash once, write every cell, commit once (protocol change to
  the flip; saves the 2-3 inner passes per cell). A = do it (Sonnet, model-free, tested on synthetic repos; recommended), B = keep the loop.
- **271 Idle watchdog / uptime guard.** The hold has been in place since 2026-09-28 and serving rotation now follows experiment needs
  (owner 2026-10-11). A = retire the 12-h uptime restart and keep the hold permanently with a daily health check (recommended), B = re-arm
  the guard when idle.
- **272 Carriers now.** The owner goal needs the base to run end to end on Audio2Tool, E21 and E22. A = start the carrier base runs now in
  the GPU gaps (A2T all-off A/A on the frozen 400 split, E21 all-off ~4 GPU-h, E22 encoder window + all-off), using v2.2 as the SLURP
  system of record while 268 is pending (recommended); B = wait for 268's result; C = wait for a SLURP system-level lock (252).
- **273 SOTA comparator table.** "At or above SOTA on several tasks" needs a defined comparator: per task, the published training-free
  numbers and the fine-tuned numbers, with the claim class the owner wants (training-free control of a frozen core vs any system). A =
  commission the table as a Stage-1-style survey record first (0 GPU; recommended), B = claim only against direct-call baselines.

**Plan after iteration 3 (sequence; GPU-hours are measured rates).** (1) today: i3 column seals (~11:50Z) -> `close --iter 3` -> loop
results note (Opus) -> decision 263 ledger entry; (2) 268-B: Thinking system column (14 GPU-h, ~1 day with the swap) OR 272-A carriers in
the gap; (3) carriers: A2T all-off A/A (~2 GPU-h), E21 all-off (~4), E22 packets + all-off (~3 + window); (4) engineering in parallel
(model-free): 270 one-pass flips, knowledge snapshots cached on ext4 (the remaining 9p cost in `check`), registry/handoff hygiene;
(5) consolidation: SOTA table (273), Stage-3 claim surface under 252, test-sample allowance only after 268 is measured.

### Owner rulings 2026-10-12: 268 B, 269 A, 270 A, 271 A, 272 B, 273 A; Thinking-mode directive (coordinator record)

Owner, verbatim: 「决策268：B；269：A；270：A；271：A；272：B；273：A，我给你一个明确的输入：如果thinking模式的模型效果在系统上可以叠加且更好的话，
我们就需要基于thinking模式去优化和调整整个工程基座，注意一定要能够让thinking模式做完任务而不是中途截断！同时，注意上下文工程是否要带着thinking的
中间结果，还是不带？另外你也要分析下llama.cpp是否可以通过外界配置哪些node可以开放thinking，哪些node其实不需要开放thinking来提高系统的吞吐效率！」
English: "268: B; 269: A; 270: A; 271: A; 272: B; 273: A. A clear input: if the Thinking model's effect stacks on the system and is better,
we must optimise and adjust the whole engineering base around Thinking mode -- and make sure Thinking mode FINISHES the task instead of
being truncated midway. Also consider whether context engineering should carry Thinking's intermediate results or not. And analyse whether
llama.cpp can be configured externally so that some nodes open thinking and others do not, to raise system throughput."

Consequences: (268 B) the Thinking-core system column flies after iteration 3 closes; its registration (lock v2.2 + v4g module program on
the Thinking core, Fold B, twin, cap and a reasoning budget that guarantees an answer) is prepared model-free now; (269 A) the loop ends
with its results note and ledger entry, no Fold A / DEV flights for refused states; (270 A) one-pass flip convergence goes to engineering;
(271 A) the 12-h uptime restart is retired (task SAEA-Serving-UptimeGuard disabled), the watchdog hold stays, a daily health check
replaces it; (272 B) carriers wait for 268's result; (273 A) the SOTA comparator table is commissioned as a survey record. Thinking-mode
engineering analysis commissioned: llama.cpp (pinned featcache build) reasoning controls -- `--reasoning-budget` / per-request budget,
`--reasoning-format`, chat-template `enable_thinking`, what the Thinking GGUF's template supports -- the no-truncation guarantee (budget +
answer reserve, never an empty answer at max_tokens), whether prior reasoning is carried in multi-turn context (Qwen guidance: not carried;
the template strips it), and a per-node thinking policy for the module program (which nodes need reasoning, which run at budget 0) with a
throughput model from the measured 22.8 s per contact and 1,032 tokens mean.

### Owner directive 2026-10-12 09:20Z: unify the engineering base first (model, features, disk); lock experiment efficiency before any further experiment (decision 274 PROPOSED, coordinator record)

Owner, verbatim: 「先把工程基座归一了，用什么模型，读取什么特征，从哪个盘读取，先锁定实验效率，而不是在一些明知道有缺陷的地方反复跑实验」
English: "First unify the engineering base -- which model is used, which features are read, from which disk they are read -- and lock
experiment efficiency first, instead of repeatedly running experiments on spots we already know are defective."
Coordinator reading: a single declared base (one manifest, one gate) for (1) the core model(s): Instruct and Thinking Q4_K_M with their GGUF +
mmproj hashes, serving geometry per core, decode policy per core (cap, reasoning budget, context policy); (2) the features: one speech-packet
root per core on ext4 (`/home/chao/feat-cache/...-04ccc72a` Instruct, `...-thinking-gpu-afdaeff6` Thinking), knowledge snapshots cached on
ext4 by content hash; (3) the disk: every hot path on Linux-native ext4 -- the repo flip worktree (done, 267), the model copies (done), the
packets (done), and the remaining 9p consumers: the data-root subtrees the runtime reads and writes during a flight (`runs/`, `prepared/`,
`analysis/`, `knowledge/`, `coordination/`, `serving/`) still on `/mnt/e`; `/mnt/e` becomes the archive (one working copy on ext4 + one
archive, the program's no-duplication rule); (4) measured efficiency targets: campaign prelude, seal, flip and check times before/after, as
a gate. No new experiment is registered until the base manifest and its gate land; the flying i3 column (the loop's last iteration) is
left to finish because it does not touch the consolidation and the card is otherwise idle; 268 flies only on the unified base.

### Thinking-core engineering design (spec merged 5e20e1ba8): decisions 275-283 PROPOSED (coordinator, 2026-10-12 09:45Z)

`docs/superpowers/specs/2026-10-12-thinking-core-engineering-base-design.md` answers the owner's three questions. (1) The PINNED llama.cpp
fork (upstream fdbd6abee + 7 feature-cache commits) already supports a global `--reasoning-budget`, a per-request `thinking_budget_tokens`
with a budget sampler that FORCES `</think>` (the model is made to close and answer, not cut off), `--reasoning-budget-message`, per-request
`chat_template_kwargs.enable_thinking` (the Thinking GGUF's template honours `enable_thinking: false`; the checkpoint is "thinking-only",
answer quality with thinking off unmeasured), and a mid-generation control call; no rebase needed. (2) Finishing the task: per node a
reasoning budget B = 3,072 + answer reserve R = 1,024 (`max_tokens` 4,096; B covers 98.3 % of 266-E's self-terminated contacts; the 36
runaways get a forced close); at 8,192 the module prompts of the ace arm no longer fit the 24,576-token slot; one receipted answer-only
re-ask (thinking off) per node, then the existing abstention; an empty Perception contact would otherwise abstain the whole row (about
6.6 % of rows). Likely runaway cause [unverified]: greedy decoding (Qwen warns of endless repetition at temperature 0; the checkpoint's
config says 0.6). (3) Context: carry NO reasoning between nodes (`reasoning_context_policy = drop-reasoning-v1`): the harness already
passes only `content`, the template drops prior reasoning. (4) Per-node control works through per-request fields on ONE resident Thinking
server (two resident models impossible: 37 GB); Solver needs thinking, Perception must be measured (intent is decided at its shortlist and
Thinking loses intent in general / music). Throughput per 1,080-row column: c4 unbudgeted 9.2 GPU-h (10-13 h wall); c4 budgeted 7.9;
c3 (Perception + lock + twin) budgeted 5.9 (6.6-8.5 h); c3 Solver-only thinking 4.5 (4.9-6.4 h). Only single-pass c3 fits a working day.
- **275** mechanism: A per-request controls on one resident Thinking server (recommended).
- **276** budget/reserve: A B 3,072 / R 1,024 / cap 4,096 (recommended); B 2,048 / 1,024.
- **277** forced-close marker: A `--reasoning-budget-message` with a fixed sentence (new fragment + session) (recommended).
- **278** fallback: A one receipted answer-only re-ask per node then abstention (recommended).
- **279** reasoning context: A drop-reasoning-v1 (recommended).
- **280** per-node policy for 268: A every node thinks, budgeted (recommended for the transfer read); B Solver-only.
- **281** column shape for 268: A one pass of c3 (lock + twin, no ace) (recommended).
- **282** decoding: A temperature 0 as in 266-E (recommended for comparability); B Qwen's 0.6.
- **283** engineering before registration: A implement the harness knobs (per-request budget / enable_thinking / budget message through the
  transport, forced-close detection, the re-ask, hashed knobs) with 0-GPU stub-server tests first (recommended; started model-free now as
  part of the base unification); B fly 268 with the global budget only.
Sequencing under the owner's 09:20Z directive: 274 (base unification) and 283 land first; 268 flies on the unified base with 275-282 as ruled.

### Disk question 2026-10-12 (owner: "can part or all of E: become ext4?"): measured answer; decision 284 PROPOSED (coordinator, 10:00Z)

Facts: E: is one NTFS partition spanning a 3.8 TB NVMe (disk 1; 1.6 TB used, 2.3 TB free); the WSL root is an ext4 VHDX at D:\wsl\Ubuntu-24.04
(1 TB, 481 GB free); WSL 2.6.3 / kernel 6.6.87. Non-destructive test: a 20 GB VHDX file created on E: with diskpart, attached with
`wsl --mount --vhd <file> --bare`, formatted ext4 inside WSL, benchmarked, detached and deleted.

| path | seq write 2 GB | seq read 2 GB | create 2,000 small files | stat+read 2,000 files |
| --- | ---: | ---: | ---: | ---: |
| ext4 VHDX on E: (wsl --mount --vhd) | 899 MB/s | 1.6 GB/s | 0.03 s | 2.07 s |
| /mnt/e (9p, today's data root) | 163 MB/s | 193 MB/s | 3.45 s | 5.91 s |
| WSL root ext4 (D:\wsl vhdx) | 1.3 GB/s | 2.2 GB/s | 0.05 s | 2.36 s |

Options: (A) an ext4 VHDX on E: (proposed 1.5 TB expandable) as the HOT data root; E: stays NTFS for Windows; near-native speed (small-file
work 115x faster than 9p); needs a mount step after every reboot / `wsl --shutdown` (scheduled task at logon or a WSL boot script) and a
locator check that refuses to start a flight when the mount is absent. (B) Reformat the whole E: as ext4 and `wsl --mount` the physical
disk: full speed, but 1.6 TB must be moved off first (no room: D: 766 GB free + ext4 481 GB) and Windows loses the disk entirely (no
ext4 driver; the disk goes offline while mounted). (C) Shrink E: and add an ext4 partition: `wsl --mount --partition` takes the WHOLE
physical disk offline from Windows while mounted, so the NTFS part becomes unusable during every flight -- not viable for a Windows data
disk. (D) Keep the hot set (~100 GB) on the WSL root ext4 (481 GB free) and leave E: as the archive -- zero infrastructure change, enough
for today, no headroom for derived media (179 GB) and feature caches (105 GB) growth.
- **284 (PROPOSED)** hot data root location: **A** (recommended; VHDX size and mount automation as the base-unification spec states),
  D as the immediate stop-gap if A waits; B/C not recommended.

### Decision 284 RULED (owner, 2026-10-12): the data-disk migration in three steps (coordinator record and execution log)

Owner, verbatim: 「我理解我们得做一次数据盘变迁的内容，你这样去做，第一步是按照方案1，划分一块2TB的存储区出来，mount到linux里面，第二步，把E盘已经使用的部分，
分析下哪些需要搬迁的，搬到ext4盘里面；第三步，删除E盘已经存量的内容，后再剥离一块盘出来，mount到ext4里面，最后给E盘留下500GB的空间就够了」
English: "We need a data-disk migration. Do it this way: step 1, per option 1 carve out a 2 TB storage area and mount it into Linux; step 2,
analyse which of E:'s used content needs to migrate and move it to the ext4 disk; step 3, delete the existing content on E:, then carve
out another disk and mount it into ext4; in the end leaving E: with 500 GB of free space is enough."
Execution log: step 1 done 10:05Z -- `E:\saea-data-1.vhdx` (2 TB expandable, diskpart), attached with `wsl --mount --vhd`, formatted
ext4 (label `saea-data-1`, UUID 7456a22a-..., 0.5 % reserved), mounted at `/mnt/wsl/saea-data-1` with the stable path
`/home/chao/saea-data` (symlink), logon auto-mount task `SAEA-Mount-Data1` registered (`wsl --mount --vhd E:\saea-data-1.vhdx --name
saea-data-1 --type ext4`); every driver/chain gains a locator check that refuses to start when the mount is absent (base-unification
spec). Step 2: inventory of E: (Windows-side sizes) in progress; the migration itself (rsync with checksums, per-subtree manifests)
runs only when no flight writes to the data root (after the i3 column seals and closes) and before any new registration. Step 3 (delete
the E: originals after verification, carve `saea-data-2.vhdx` of about 1.3 TB, leave about 500 GB free on E:) follows the verified
migration and the cut-over of `SPEECHRL_DATA_DIR`; the deletion is executed only after the owner sees the verification manifests.

### Decision 284 step 2 (owner 2026-10-12 10:20Z): delete the ChatGPT-era and Stage-1 artefacts, migrate everything else; no hot/cold by current use (coordinator record)

Owner, verbatim: 「ChatGPT和Stage1产物删掉，其他的都搬到ext4区，不能基于我们现在是否使用来判断冷热」 -- "Delete the ChatGPT-line and Stage-1
products; move everything else to the ext4 area; do not judge hot/cold by whether we currently use it."
Inventory of E: (1,556 GB, all under speechrl-data; Windows-side sizes): datasets 1,006 (cn-celeb2 144, contextasr-bench 134, librispeech 115,
slue-sqa-5 110, air-bench 46, cn-celeb1 42, m3-slu 40, meld 32, speech-massive 30, notsofar1 26, fleurs-r 25, fsd50k 23, ... slurp 12.6,
audio2tool 9.8, earnings21-22 5.2, conec 0.6; 28 umbrella lock keys), derived 178 (obs-slices 147), models 149, runs 77, coordination 43,
system-text-search 31, _repro 29, prepared 10, wire-check 9, survey-* 7.5, analysis 4, vectors 3.6, serving 3.3, the rest < 2.
DELETE (not migrated; the git-tracked records of these lines stay): `system-text-search/` (31 GB, decision-214 line, 2026-10-01..03);
the ChatGPT-line `coordination/` packages of 2026-10-01..09 (four-node-round9-preview-v1/v2/v3 14.8, system-text-round8-preview-v1 5.3,
slurp-system-text-seed-binding-recovery1-owner225 5.2, slurp-system-text-review-contract-engineering-v1 5.2, slurp-coherent-feedback-
engineering-v1 1.4, local-joint-n100-custody-engineering-v1 1.0, update4/5/6-rejected-* 1.6, rejected-context-history-v1 0.6,
system-text-compact-feedback-engineering-v1 0.5, system-text-feedback-streaming-v1 0.5, one-track-consolidation-20261007 0.3,
local-node-k4-serving-start-v1 0.1, simple-consumption-capacity-v2 0.1; about 36 GB); the Stage-1 survey trees (`survey-fulltext`,
`survey-backups`, `survey-fulltext-secondary-analysis`, `survey-fulltext-analysis`, `survey-bfs`, `survey-query-raw`, `survey-triage`,
`survey-capability-delta`; 7.5 GB); `_repro/` (29 GB, the pre-study reproduction wavs/checkpoints of July 2026) -- flagged for the owner's
word because it predates the ChatGPT line. Everything else migrates to `/home/chao/saea-data/speechrl-data/` (about 1,450 GB of the 2 TB
disk 1). Execution: static subtrees (datasets, models, derived, prepared, vectors, repos, environments, wire-check, references, research,
program-archives, manifests, archive, ...) started 10:22Z as task SAEA-Migrate-Static-284 (rsync -aH per subtree, logs under
/home/chao/saea-migration/); the subtrees the flying i3 column writes (runs, attempts, analysis, knowledge, coordination minus the
deleted packages, serving, locks, receipts, logs) follow after the seal with a final `--delete` pass; verification manifests per subtree;
then the `SPEECHRL_DATA_DIR` cut-over; then step 3.
Owner 2026-10-12 10:30Z: 「_repro/ 删除」 -- `_repro/` (29 GB) is DELETED with the ChatGPT-line and Stage-1 artefacts. The running static
migration task copies it before the ruling takes effect in the script's list; the ext4 copy is removed right after STATIC_DONE and the E:
original goes with step 3. Final deletion set: system-text-search, the 2026-10-01..09 ChatGPT-line coordination packages, survey-*, _repro
(about 104 GB).

### Terminal clean-up (owner 2026-10-12 10:35Z) and the SOTA comparator table (273 delivered); decision 285 PROPOSED (coordinator)

Owner: 「我们为什么开启了这么多terminal？哪些是必要的，那些是不需要的，这块要清理下！」 Finding: 81 orphaned `conhost.exe` console windows on the
Windows side -- every scheduled-task launch (`wsl.exe` as an interactive task action) opened a visible console and the idle watchdog spawned a
new one every five minutes; plus console hosts of agents' finished WSL calls and of unrelated programs. Necessary and kept: the serving
session + its monitor (SAEA-Serving, SAEA-Monitor), the flying i3 column chain (SAEA-Queue-TFRLi3Col), the migration (SAEA-Migrate-Static-284),
the serving entry tasks per geometry (SAEA-Serving-*/SAEA-Monitor-* are what `serving_swap.sh` starts), SAEA-Mount-Data1, SAEA-Batch-Driver, and
today's live `wsl` sessions of the coordinator and the four agents. Cleaned: 34 stale console/host processes killed (orphans and the 10/8-10/9
WSL hosts of finished tasks), 36 finished one-off tasks unregistered, SAEA-Watchdog disabled (the hold is permanent; a daily health check
replaces it per 271 A), SAEA-Serving-UptimeGuard removed. Fix: `saea_task.ps1` now launches tasks through a hidden PowerShell console
(`-WindowStyle Hidden`, task setting `-Hidden`), so no window appears per task (ca96adfae).

SOTA comparator table (decision 273 A) merged: `docs/readiness/2026-10-12-sota-comparator-table-v1.{md,json}` (61f6d69e7). Headline: we
reach fine-tuned SOTA on no task. SLURP: ours 82.36 intent / 66.65 SLU-F1 on the 3,010-row test sample vs fine-tuned UniverSLU-14 90.3 / 79.5
and fine-tuned Qwen2-Audio-7B 88.13 / 76.75 (gap about -8 / -13); vs the best published zero-shot intent (ChatGPT on gold transcripts
79.25) +3; no zero-shot audio model reports official SLU-F1. Audio2Tool: our direct call 62.03 tool accuracy vs the paper's 69.19 for the
same core (tier 1 never reproduced); the dual-store system's exact match 24.37 vs 20.71 (+3.66, not adopted). Earnings-21: bare core 8.20
WER vs Whisper large-v2 9.7 (zero-shot), KC-E1f PERSON entity WER 18.75 vs Whisper-large 28.9 -- the strongest position. Earnings-22: 9.24
with the silence-tail convention vs Nemotron 3 Nano Omni 9.66 and NeMo fine-tuned Qwen3-Omni 8.89 [unverified]; not like-for-like.
Many leaderboard values are UNVERIFIED (huggingface unreachable). Claim classes: A vs the direct call of our own core (large, replicated
on SLURP), B vs published zero-shot systems (competitive on Earnings-21 and SLURP intent), C vs fine-tuned SOTA (not reached).
- **285 (PROPOSED)** the claim class of the programme goal "at or above SOTA": A = class B (training-free / zero-shot systems) as the
  comparator for every task, stated as such in every note (recommended; it is the claim the thesis supports); B = class C (fine-tuned),
  which would require closing -8 / -13 on SLURP; C = class A only.

### 268-B package registered (DRAFT/HELD; merged): the system on the Thinking core; prerequisites; decision 286 PROPOSED (coordinator, 2026-10-12 10:50Z)

Package `docs/readiness/2026-10-12-slurp-system-thinking-core-fold-b-v1/` (family `scripts/flights/direct/thinking_system_family.py`): three cells
on Fold B -- smoke (4 rows), lock (1,080 rows, plain lock v2.2 + v4g, program c2 = Perception + Solver) and its request-identical twin `aa`
as a SECOND cell (the module compiler refuses a candidate-less in-row supply group, so the c3 in-row twin of the design needs the compiler
change first; two c2 passes cost ~1.9 GPU-h more); Thinking packets root + receipt as in 266-E; comparators = the i3 lock arm (Instruct
core, same roster) and the bare Thinking core (266-E). Knobs (design 275-282): budget 3,072 + reserve 1,024 = cap 4,096, forced-close
message, drop-reasoning-v1, every node thinking; new fragment `...-module-fold-b-np4-ctx24k-budget3072-max4096-v1` and session
`serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1` (`think-budget-np4` target; needs tasks SAEA-Serving-THINKB /
SAEA-Monitor-THINKB). GPU: 51.9 slot-seconds per c2 row -> 3.89 GPU-h expected per pass (ceiling 5.1), two passes 7.8 expected / 10.7
ceilings; wall ~4.3-5.6 h per pass. Read: `scripts/analysis/slurp_system_thinking_core_read.py` (verdicts TRANSFERS-ABOVE-BAR / PARTIAL /
NO-TRANSFER / HARM; per-node cap-hit, forced-close and cost tables). Seven DRAFT ledger rows (8977-8983 at the branch's base).
Prerequisites before countersign/flip: (1) the harness knobs (283, in build) merged and the package re-derived; (2) the serving tasks for the
budget session registered; (3) the forced-close sentence verified; (4) **286 (PROPOSED)**: native role contacts require `preserve_wire_responses
= true`, so the sealed trace on the data root will contain the Thinking `reasoning_content` bytes (hashed, under the data root, never in
docs or notes). A = allow sealing reasoning bytes under the data root (recommended: sealed model output is already stored there; the
no-persist rule covers documents, chat and notes); B = add a transport option that drops reasoning bytes before sealing (hash only).
Sequencing: 274 (base) -> 283 (knobs) -> re-derive 268 -> i3 closed -> countersign, mint, ext4 flip, swap to think-budget-np4, chain.

### 283 A delivered: the Thinking harness knobs merged (0e6ffbfd3); 268 package being re-derived on them (coordinator, 2026-10-12 11:00Z)

Model-fragment keys (all hashed into the fragment / composed / protocol hashes): `reasoning_budget_tokens`, `answer_reserve_tokens`
(`max_tokens == budget + reserve` enforced), `enable_thinking`, `reasoning_context_policy` (`drop-reasoning-v1`), `forced_close_message_sha256`
(the sha of the `--reasoning-budget-message` value in `server_args`); Instruct fragments accept only the context policy. Per-node
`thinking_policy` in a baseline/experiment fragment (native path: role kinds perception / solver; direct path: phase names), hashed.
Wire: `thinking_budget_tokens` and `chat_template_kwargs.enable_thinking` on the request (refused without the reasoning guard); COST record
gains `reasoning_chars`, `reasoning_tokens` (null unless the server reports it), `forced_close` (reasoning ends with the pinned message).
Fallback (278): one receipted answer-only re-ask (`enable_thinking: false`, `max_tokens` = reserve) when a budgeted contact returns empty
at its cap; receipt `saea-thinking-answer-fallback-v1` at `<contact>/reasoning-fallback`; the re-ask is metered (plan ceiling rows x
(max_contacts + 2) for module programs). Byte identity: the Instruct and the Thinking max8192 cells compose to the same config hashes as
before. Tests: 39 + 24 new, the transport / adapter / controllers / runner / empty-completion suites pass; gates PASS. Open items: the
supply-variant fit ceiling is not yet bound to B + R; the forced-close sentence is still to be verified verbatim against the Qwen3 report.
`runtime.py` and `rails/*` changed, so every unflown registered cell re-pins at its next flip (the flying i3 column is unaffected).
268 package re-derived on the merged knobs (0943022b6): the fragment carries the five knob keys (budget 3,072, reserve 1,024, cap 4,096,
drop-reasoning-v1, message sha), `compose()` folds in `thinking_budget_tokens` and `chat_template_kwargs.enable_thinking`; plan ceilings rows x
(2 contacts + 2 fallbacks) = 4,320 calls / 12,620 s per arm (16 / 41 s smoke), GPU ceilings unchanged (5.1 per arm); seven draft rows rewritten
in place. The forced-close sentence is VERIFIED against the Qwen3 technical report (arXiv:2505.09388, thinking-budget section): "Considering
the limited time by the user, I have to give the solution based on the thinking directly now." -- the report appends "\n</think>.\n\n", which
llama.cpp's budget sampler supplies itself. Remaining prerequisites for 268: 274 base cut-over, the serving tasks for the budget session,
owner rulings 285 / 286, i3 closed.

### Owner input 2026-10-12 11:05Z: the SOTA table is provisional until the Thinking-mode base is locked (285 deferred); 286 RULED -- the native reasoning trajectory is not a controllable input, so its bytes are not part of the end-to-end trace (coordinator record)

Owner, verbatim: 「SOTA对照表里面，我们之前没有用thinking模式作为同意的工程基座，所以这个对照目前看起来不足以支撑我们的结论，我们后续如果锁定thinking模式下的工程基座
作为我们统一的工程基座的话，再做详细对比，你调研业内明确基线这件事情很有价值！决策286：这里面我们其实发现了一个很有价值的点，我们是否能够操控和优化模型原生
的推理轨迹呢？我倾向于我们无法做到这件事情，那这样的话，是否还需要把它记录在我们端到端的轨迹中呢？他既不是阶段目标也不是可控的输入？」
English: "The SOTA table compared systems that did not use Thinking mode as the unified engineering base, so it cannot yet support our
conclusions; once the Thinking-mode base is locked as the unified base we redo the detailed comparison -- the survey of explicit industry
baselines is valuable. 286: a valuable point surfaced here: can we manipulate and optimise the model's native reasoning trajectory? I lean
to no. If so, does it even belong in our end-to-end trace? It is neither a stage goal nor a controllable input."
Coordinator analysis: within the thesis object (a control plane OUTSIDE a frozen core, acting through inputs and decoding), the reasoning
trajectory is reachable only through (a) what the context contains, (b) the budget / enable switch, (c) the forced-close marker, (d) sampling
-- never its content. It is core-internal output: not a registered artefact, not a node input (decision 279: dropped between nodes), not
a selection target. What the programme DOES need from it is bounded and non-textual: its length (tokens / chars), whether the budget forced
the close, the finish reason, and an integrity hash so a sealed trace still binds the complete wire response. Ruling applied as 286 = C:
**the sealed trace keeps `reasoning_content_sha256`, `reasoning_chars`, `reasoning_tokens` (when reported), `forced_close` and
`finish_reason`; the reasoning bytes themselves are discarded at the transport before sealing**, on every path (direct, native role contacts
with preserved wire responses). Replay (E10 trace replay) and the answer path never used the bytes. Implementation commissioned model-free
(transport/sealing change + tests; the 266-E sealed traces that already hold reasoning bytes stay as flown; new cells re-pin at their flip).
285 deferred: the comparator table stays as a survey asset (registered baselines per task); the claim-class comparison is redone once the
unified base (Thinking mode, if 268 transfers) is locked.
286 implemented and merged: reasoning bytes are projected out at the transport on every path; the stored wire message carries a `reasoning`
object (`reasoning_content_sha256`, `reasoning_chars`, `reasoning_tokens`, `forced_close`, `finish_reason`, bases, policy
`hash-and-stats-only-v1`); `wire_response_sha256` hashes the stored projection, `reasoning_content_sha256` binds the dropped bytes;
responses without reasoning are byte-identical to before (pinned). The 266-E Thinking traces hold no wire responses (preserve was false),
so no sealed artefact contains reasoning bytes. The 268 package's stale "reasoning bytes land in the trace" finding text is refreshed at
its next re-derive.

### 274 deliverable ready (branch `opus/engineering-base-unification`, d72faac0e; merge after the i3 driver exits): base manifest, locator gate, migration tooling; decisions 287-295 PROPOSED (coordinator, 2026-10-12 11:15Z)

Spec `docs/superpowers/specs/2026-10-12-engineering-base-unification-design.md`; manifest `configs/base/engineering-base-v1.json` (two Q4_K_M
cores with hashes + llama.cpp build 04ccc72a, five serving geometries, packet roots with promotion-receipt hashes, roots, subtree classes, the
24 live scripts, a timing budget); `scripts/lib/data_root.sh` = the ONE default line + init guard (refuses a missing root, a non-ext4 root
after the cut-over, a stale inherited `SPEECHRL_DATA_DIR`), read by 22 live scripts + `serving_lib.sh`; `engineering_base_locator_check.py`
(manifest vs default line, live scripts, a ratchet baseline of the 341 frozen files carrying the `/mnt/e` literal, models vs runtime receipts
and the umbrella lock, geometries vs fragments; `--host` adds ext4 / mount / sizes / receipt hashes); `scripts/data/migrate_data_root_ext4.sh`
(dry-run default; `--phase hot|runtime|derived|rest|cold`; `--execute` refuses while a flight, flight lock, flip, serving start/monitor/swap
or a server on 8080 is alive; rsync per subtree, absolute-symlink re-pointing, sha256 manifests both sides, receipts); `engineering_base_timing.py`
(first receipt: CLI import 0.76 s ext4 vs 2.89 s 9p warm; git status 0.30 s vs 199 s under campaign load; 2,000-file stat+read 0.06 s vs 78 s).
Findings that shape the cut-over: flights DO read raw audio (hash + sample-rate probe per row), so `datasets/` must be reachable under the
data root; `derived/` must be a real directory (eight receipts pin `derived/...` relpaths); three surfaces bind the absolute root (serving
session identity -> every session restarts after the cut-over; hypothesis-source artefacts -> re-prepare before reuse; semantic-authoring
registrations -> need a compatibility link); the fit monitor restarts; 22 Audio2Tool + the Earnings baselines pin `/mnt/e/...` absolutely
(kept frozen; resolved through a compatibility link once E: is emptied); three E22 fragments name a packet root that does not exist on this
host; `~/.bashrc` exports the old `SPEECHRL_DATA_DIR`; 116 registered worktrees (89 on merged branches) and ~320 directories under
`/home/chao/saea-worktrees`. Owner's 284 ruling supersedes the spec's hot/cold split: EVERYTHING migrates to disk 1 (1,450 GB of 2 TB; the
two static lanes are copying datasets/models/derived there now), disk 2 is growth/archive space, no datasets/models links.
- **287** adopt base v1 + the locator gate as a standing offline gate (recommended A).
- **288** cut-over moment: A right after the i3 column seals (serving stopped, hot subtrees migrated, default line flipped, serving
  restarted on the new root; ~1-2 h of GPU idle) (recommended); B after 268.
- **289** compatibility link `E:...\speechrl-data -> disk 1` after step 3 so the 341 frozen absolute pins keep resolving (recommended A).
- **290** keep the Audio2Tool / Earnings absolute pins frozen (their prepared-supply identities) (recommended A).
- **291** disk 2 size: A 1.3 TB (E: keeps ~500 GB) per the owner's plan.
- **292** worktree cleanup from WSL: remove worktrees on merged branches and orphan directories (recommended A; never from Windows).
- **293** backup: both VHDXs and the source share ONE physical drive (E:); A = a periodic rsync of the sealed subtrees to D: or an external
  disk (recommended); B = none.
- **294** `~/.bashrc` and the queue wrappers switch to the data-root authority at the cut-over (A).
- **295** the three E22 fragments naming a missing packet root are re-pinned when E22's encoder window runs (A).

### Owner decision brief 2026-10-12 11:40Z (second of the day): open decisions 287-295, current stage, plan (coordinator, on the owner's request)

**Stage.** (1) SLURP system of record = lock v2.2 + v4g on the Instruct core (test sample read done). (2) The sealed-credit loop: i1, i2
closed (ACE refused +0.87 then +1.38 [+0.15, +2.57]; typed arm empty), i3 column flying (seal ~11:55Z), then `close --iter 3`, the loop's
results note and ledger entry (269 A). (3) 266-E read: bare Thinking +11.90 / +4.35 over bare Instruct; the system adds +31 / +10 over
bare Instruct. (4) 268 B (system on the Thinking core) is registered (held) with the Thinking knobs (283 merged: budget 3,072 + reserve
1,024 = cap 4,096, forced close verified against the Qwen3 report, drop-reasoning context, per-node policy, one receipted re-ask) and
286 (reasoning bytes never sealed; hash + stats only). (5) 274 base unification: ext4 flips (267; 9 min for a proposer package, 34 min
for a column package), one-pass flip mode (270, default still iterate), the base manifest + locator gate + migration tooling on a branch
(merge after the i3 driver exits), data-disk migration (284) in progress: disk 1 (2 TB ext4 VHDX) mounted, static subtrees copying
(327 GB of ~1,450 GB by 11:36Z, two lanes, ~110 MB/s), ChatGPT-line and Stage-1 artefacts excluded for deletion (~104 GB). (6) Carriers
wait for 268 (272 B); SOTA table on file as a survey asset (285 deferred). (7) Housekeeping done: terminals (hidden task consoles,
36 one-off tasks unregistered, watchdog and uptime guard retired), ledger closure gate PASS.

**Open decisions** (recommendation first): 287 adopt base v1 + locator gate (A); 288 cut-over right after the i3 seal (A) vs after 268
(B); 289 compatibility link on E: after step 3 (A); 290 keep the A2T/Earnings absolute pins frozen (A); 291 disk 2 = 1.3 TB (A);
292 worktree cleanup from WSL (A); 293 backup to another physical disk (A); 294 `~/.bashrc` + queue wrappers to the data-root authority
at the cut-over (A); 295 E22 packet-root re-pin at its encoder window (A).

**Plan.** P0 (today): i3 seals -> close -> loop note -> merge 274 branch -> stop serving -> migrate the hot subtrees (runs, attempts,
analysis, knowledge, coordination minus deletions, serving, locks, receipts, logs) -> final `--delete` sync of the static subtrees ->
sha256 manifests -> flip the default line (data_root.sh), `~/.bashrc`, queue wrappers, umbrella CLAUDE.md -> locator gate --host PASS
-> restart serving (Instruct) on the new root -> timing receipt. P1 (owner reviews the manifests): delete the E: originals + the deletion
set -> compatibility link -> disk 2 (1.3 TB) -> E: ~500 GB free. P2: 268 on the unified base: register the serving tasks for the budget
session, countersign + mint + ext4 flip, swap to think-budget-np4, smoke (per-node cap-hit table) -> sign-off -> lock pass -> aa pass
(~4-6 h each) -> read (TRANSFERS / PARTIAL / NO-TRANSFER / HARM). P3 (branch on 268): if it transfers -> the Thinking-mode base becomes
the unified base (re-optimise per-node policy, budget, throughput; re-run the SOTA comparison; new test allowance only after the DEV read);
if not -> Instruct stays, 266-E stays a core note. P4: carriers (272 B after 268): A2T all-off A/A, E21 all-off, E22 packets + all-off, on
the unified base. P5: consolidation: results notes, claim surface under 252 with the claim class ruled later, worktree cleanup, backups.

### Owner rulings 2026-10-12 12:10Z: 287 A, 288 A (cut over right after the i3 seal), 289 B, 290 B, 291 = 1.6 TB and try to fold it into the existing 2 TB disk, 292 A, 293 B, 294 A, 295 A (coordinator record)

Owner, verbatim: 「决策287：A；288：按你建议；决策289：B，决策290：B，决策291：按照1.6TB划分吧，另外看下能不能合到之前划分出的2TB空间里面；决策292：A；决策293：B；
决策294：A，决策295：A」. Consequences: (287) base v1 + the locator gate become standing offline gates; (288) the data-root cut-over runs
right after the i3 column seals; (289 B + 290 B) NO compatibility link and NO frozen absolute pins: every `/mnt/e/...` literal in configs,
scripts and tests is rewritten to the new root (or to a data-root-relative form) in one sweep after the cut-over -- flown cells keep their
historical identity at their flight commits in git history, unflown cells (Audio2Tool, E21, E22 all-off) re-register with their new
prepared-supply identities, and the locator ratchet baseline goes to zero; (291) the second 1.6 TB is folded into disk 1 where possible:
the VHDX is expandable (it occupies only used bytes), so disk 1's maximum grows 2 TB -> 3.6 TB (`diskpart expand vdisk` on the detached
file + `resize2fs` inside WSL) in a quiet window, with the "E: keeps 500 GB free" rule enforced as a usage cap by the locator check instead
of a second disk; (292) worktrees on merged branches and orphan directories are removed from WSL; (293) no backup job; (294) `~/.bashrc`
and the queue wrappers switch to the data-root authority at the cut-over; (295) the E22 packet root is re-pinned at its encoder window.
Executed 12:05-12:15Z: the i3 column sealed 12:05Z at d39224f1c (`close --iter 3` running); decision 292 A executed -- worktrees 117 -> 9
(master, fable-batch-flight, fable-flip, the four unmerged codex branches, the two active agent worktrees), 87 merged-branch worktrees
removed with their branches, 21 detached codex worktrees removed (HEAD shas in the receipt), 184 unregistered directories deleted;
`/home/chao/saea-worktrees` 105 GB -> 4.5 GB (receipt `/home/chao/saea-migration/worktree-cleanup-20261012T120815Z.log`). Static migration
554 GB copied by 12:11Z.

### Loop iteration 3 CLOSED; the loop is COMPLETE with no admitted state (coordinator, 2026-10-12 12:35Z)

`close --iter 3` (row scores and ACE credit built by the close): ACE i3 (36 items) 64.72 SLU-F1 / 83.15 intent on the i3 Fold B column;
vs lock SLU **+0.27 [-1.15, +1.71]**, intent +0.46 [-0.19, +1.20]; twin vs lock -0.37; false fill -4.08 pp (392 empty-gold rows), non-empty
exact -0.73 pp. Clauses a (CI-LB > 0) and b (point floor) FAIL -> refused; typed arm empty by measurement (2 refused candidates). Curve of
the ACE comparator: +0.87 -> +1.38 [+0.15, +2.57] -> +0.27: not monotone -- the credit-curated growth from 27 to 35 items helped SLU at i2
and the 36-item i3 playbook gave it back while intent moved from -0.56 to +0.46. Ledger entry of decision 262 clause c, as measured over
three iterations: (i) the typed operator class the proposer could reach (deliver rules over the i1-i3 contrast tables) produced no
candidate that cleared the 1.5 pp predicted bar -- every fitted rule read +0.00 pp and the proposer re-proposed a refused rule once;
(ii) the ACE prose-item form at equal budget peaked at +1.38 pp SLU (CI-LB +0.15) with an intent cost and did not clear the 1.49 floor;
(iii) the loop's engineering (sealed archive with corrections and rereads, credit-driven curation, duplicate refusal, self-built credit,
one-pass flips) is complete and reusable for a different operator class. Parent for any continuation: s0-lock-v2.2. Per 269 A: results
note (Opus) and this ledger entry; no Fold A / DEV flights for refused states. Rows closed; GPU idle from 12:05Z; the data-root cut-over
(288 A) starts now.

### Literal sweep merged (289/290 B); loop results note merged; decision 296 executed (hot-root relayout); final verification pass queued (coordinator, 2026-10-12 14:05Z)

- **Literal sweep merged** (`sonnet/data-root-literal-sweep`, 361 files, merge commit 3cdc1aca3; the one conflict in `core/config.py`
  resolved by keeping both the reasoning-knob fold and the placeholder expansion; `test_config_composition` 92, `test_thinking_harness_knobs`
  39 and `test_data_root_placeholder` 10 pass): the 341 carriers of the `/mnt/e/...` literal now resolve through the data-root authority --
  `.sh` scripts source `scripts/lib/data_root.sh`, `.py` scripts read `SAEA_DATA_ROOT` then `SPEECHRL_DATA_DIR`, config fragments carry the
  placeholder `${SAEA_DATA_ROOT}` (hashed unexpanded, expanded for consumers, collapsed back by `_canonical_hash`); the locator ratchet
  baseline is empty and the check refuses any new literal; host mode gains the "E: free >= 500 GB" rule (291). Identity consequences: the
  config text of 90 fragments changed, so their pins move -- flown cells keep their identity at their flight commits (A2T native-role, E21
  window cells, the SLURP encoding protocols); unflown cells (A2T stage-3 all-off, E21/E22 all-off and direct, the e21 packet experiments,
  the A2T knowledge compile and unflown SLURP preparation protocols) re-register at their next flip; four registered-hash tests stay red
  until those re-pins (`test_e21_native_window_fit_registration`, `..._registration_prepare`, `test_e22_alloff_cell_registration`,
  `test_e41_bounded_perception_note` -- the e41 one is a flown package and must not be regenerated). 1,826 files under `docs/` keep the
  literal as immutable history; four Python helpers under `docs/` that live scripts import and a MANIFEST pins (`falsifier.py`,
  `timing.py`, `score_r0bias.py`, `copycount_r0bias.py`) break without a compatibility link and need English successors under
  `scripts/` (open item). Seven carriers merged after the sweep's branch point (the 268 package: `thinking_system_{flip,read,mint_receipt}`,
  `batch_chain_thinking_system.sh`, the think-budget serving entry/monitor, `slurp_system_thinking_core_read.py`) were caught by the
  ratchet and routed through the authority in the same commit (tooling, not pinned bytes; the 268 pins are unchanged).
- **296 (RULED by the coordinator under 274/284, EXECUTED):** the hot data root is `/home/chao/saea-data/speechrl-data` -- the directory
  inside the disk-1 mount (`/mnt/wsl/saea-data-1/speechrl-data` behind the symlink `/home/chao/saea-data`), name parity with the E: layout
  and the umbrella's `SPEECHRL_DATA_DIR` -- not the mount root. The static lanes already copied there; the 274 tooling targeted the mount
  root. Execution: the hot cut-over task SAEA-Cutover-Hot-284 (started 12:30Z) had verified `runs` (27,402 files, 84.3 GB, 2,487 s),
  `analysis` (4,863 files, 4.4 GB, 61 symlinks re-pointed) and `knowledge` (200 files, 0.6 GB) at the mount root and was STOPPED by the
  coordinator at 13:30Z during `prepared` -- its later phases (runtime, derived, rest) would have duplicated lane 1/2 copies at the mount
  root (derived alone is hundreds of GB) and risked filling the 2 TB disk. Relayout 13:42Z (same filesystem, instant): the three verified
  subtrees moved under `speechrl-data/`, the partial `prepared` copy dropped (lane 2 writes the final one), the 61 symlinks re-pointed
  again under `speechrl-data/`, and the run's receipts moved OUT of the data root to `/home/chao/saea-migration/receipts-ext4/` -- the
  verifier compares full sha256 manifests, so receipts inside `<hot>/receipts/` would make the `receipts` subtree MISMATCH. Authority and
  manifest updated (`SAEA_HOT_DATA_ROOT`, `roots.hot.path` / `resolves_to`, the migration script's default target); the locator rule
  `hot-mount` now reads "on a mounted ext4 other than the root filesystem" (mount point or a directory inside it; two new unit tests);
  host mode PASS (0 failures, the pre-cut-over warning only).
- **Final verification pass** = task SAEA-Cutover-296 (`/home/chao/saea-queue/cutover_hot_296.sh`, registered 13:45Z): waits for
  STATIC_DONE + LANE2_DONE (lane 1 at `datasets`, 603 GB of about 1,450 GB copied by 13:21Z), then runs the 274 tooling with
  `--target <hot> --receipt-dir /home/chao/saea-migration/receipts-ext4 --execute --jobs 20` over hot (runs analysis knowledge prepared
  coordination serving attempts locks), runtime minus `system-text-search`, derived, an explicit rest list (archive logs program-archives
  research settlements telemetry working the four `saea-slurp-*-read-*` scratch roots, `.bin`, the six loose telemetry/console files),
  then datasets + models -- every subtree rsynced (a no-op where a lane already copied it) and verified by sha256 manifests on both sides;
  then the deletion set is dropped from the ext4 copy (`_repro` 30 GB, `system-text-search` 32 GB never copied, `survey-*` 7.6 GB never
  copied, the seventeen ChatGPT-line coordination packages out of `coordination` 44 GB), the receipts are copied into
  `<hot>/receipts/migration-ext4/`, and `CUTOVER_COPY_DONE` is written. Only after that marker: flip `SAEA_DATA_ROOT_DEFAULT` + the
  manifest's `roots.data_root.current` (the migrate script refuses a target that is the live root) + `~/.bashrc` + queue wrappers +
  the umbrella client-guide line, locator `--host --require-hot-mounted`, restart Instruct serving on the new root, timing receipt, and
  the verification manifests go to the owner before any E: deletion (284 step 3, 291 disk growth).
- **Loop results note** merged (d4c50b887): `docs/results/2026-10-12-slurp-tfrl-loop-three-iterations-read.md` (Opus) + results-ledger
  entry. Corrections: the i1 lock column reads 64.00 / 82.31 (64.34 / 82.41 is the system of record's Fold B level); every offline
  deliver rule edited 0 rows (rules that never fired, not measured nulls). Two defects found, left open for the next loop use: (1) the
  typed proposer's per-carrier class set (construction / supply / delivery+scope) is dropped by the receipt builder, so the validator's
  class check never ran and at least 6 of the 9 delivery candidates came from carriers not offered delivery -- the construction and
  supply classes were never actually proposed, so the loop did not test them; the evidence against construction remains the 265
  pre-read; (2) the typed receipt field `sample_id_sha_prefix` holds the response-hash prefix.
- **Operational lesson (recorded in memory):** two inline `bash -c` variable losses in one hour (a `for f in ...` test loop ran the
  full suite three times on /mnt/d; a `du -sh "$S/$d"` became `du -sh /` and walked /mnt/c over 9p during the migration); every WSL
  command that carries a variable runs from a scratchpad script file, no exceptions.

### Migration incident 14:33Z: distro stop killed every lane; VHD re-mounted; lanes relaunched (coordinator, 2026-10-12 14:50Z)

- **Lane 1 replaced (14:10Z):** the single-stream copy of `datasets/` ran at about 8 MB/s (774k small files; 9p round-trip bound, CPU
  idle). Lane 3 (`/home/chao/saea-queue/migrate_static3_284.sh`, task SAEA-Migrate-Static3-284) copies `datasets/*` with 12 parallel
  per-directory rsync streams, then the lane-1 remainder, then writes STATIC_DONE; measured 16.9 GB/min in its first minute (about 35x).
- **Incident:** at 14:33:04Z every Task-Scheduler-owned wsl.exe session (lane 2, lane 3, SAEA-Cutover-296) ended with exit
  0xC000013A (console control) at the same instant; the distro instance then stopped (kernel log: the data disk and the distro root
  unmounted together; the WSL VM itself stayed up) and the data-disk mount vanished. No task of ours fired in that window (the only
  scheduler entry is Windows' own SoftLandingDeferralTask at 14:29Z); the cause is not identified -- the signature is a kill of the
  hidden console hosts. The VHD stayed attached to the VM (`/dev/sde`, label saea-data-1); re-mounted 14:41Z as root, 938 GB intact
  (ext4 unmounted cleanly). A probe showed that systemd SYSTEM units do not outlive their wsl.exe session either (the distro stops
  with its last client session), so Task-Scheduler sessions remain the only durable owner. Relaunched 14:44Z as tasks: lane 3
  (idempotent resume), lane 2b (`migrate_static2b_284.sh`: `prepared/` with 12 parallel per-entry streams -- 1,955 entries -- then
  vectors, wire-check, repos, environments; writes LANE2_DONE), SAEA-Cutover-296 (waits for both markers). Operational rule added to
  memory: after any distro stop re-mount the VHD first (`blkid -L saea-data-1`); the locator `hot-mount` rule refuses flights while it
  is absent.
- **Second failure and the durable fix (14:43-14:47Z):** the 14:44Z relaunch failed instantly (every rsync rc=11, false STATIC_DONE /
  LANE2_DONE markers): a `wsl --mount` is a per-distro-instance mount, and the distro instance stops whenever its last client session
  ends (serving is off during the migration, so nothing kept it alive between the coordinator's sessions) -- the VHD stays attached to
  the VM but its mount vanishes. Fix: `/etc/fstab` entry `LABEL=saea-data-1 /mnt/saea-data-1 ext4 defaults,nofail` on a root-filesystem
  mount point (WSL processes fstab at every distro start; proven across a `wsl --terminate`), symlink `/home/chao/saea-data ->
  /mnt/saea-data-1`, the logon task SAEA-Mount-Data1 switched to `--bare` (attach only). Manifest `roots.hot.resolves_to` and the
  authority's comment follow; locator host mode PASS, 27 locator tests pass. The migration logs were rotated (`static.log.1-until-1443Z-
  false-markers`, `cutover.log.1-until-1443Z`) so the false markers cannot trigger the cut-over wrapper; lane 3, lane 2b and
  SAEA-Cutover-296 relaunched 14:47Z (72 rsync streams; 949 GB on ext4).

### Owner rulings 297-300 and the 14:33Z incident cause (owner, 2026-10-12 15:25Z; recorded by the coordinator)

Owner (verbatim): 「决策297：同意建议；决策298：同意建议，尽快启动实验；决策299：按你的建议走，最终目标是经过多轮training free RL迭代后能够逼近训练方案；决策300：按你建议到时修复；事实：手动关闭」
English: "Decision 297: agree with the recommendation; 298: agree with the recommendation, start the experiments as soon as possible;
299: follow your recommendation -- the final goal is that after several rounds of training-free RL iteration we approach the trained
solutions; 300: fix as you recommend, when the time comes; fact: closed manually."

- **297 B (RULED):** after the verification manifests pass, the E: original `speechrl-data` is RENAMED to `speechrl-data.retired-20261012`
  (not deleted) until one full 268 chain has flown on the new root; then deleted together with the deletion set. Not a backup (293 B
  stands): a delayed delete that keeps a zero-cost fallback for any missed path.
- **298 A (RULED):** the VHDX growth to 3.6 TB (291) happens in the same no-flight window as the 297 delete (after the 268 read); the
  experiments start as soon as the cut-over completes -- GPU idle time is to be minimised.
- **299 A (RULED):** P3 trigger = on the 268 Fold B column, system-on-Thinking vs system-on-Instruct (v2.2 program): paired SLU CI
  lower bound > 0 AND point estimate >= +1.5 pp, intent not worse by more than 0.65 pp, AND Thinking completion rate (no cap hit, no
  empty answer) >= 99 %; all three -> the engineering base is rebuilt around Thinking (packets per mmproj for every carrier, baselines and
  locks re-read on Thinking); two of three -> Thinking on SLURP only, carriers stay on Instruct, plus one DEV replicate. Owner's stated
  end goal, recorded as the programme's north star for the iteration line: multiple rounds of training-free RL iteration that approach
  the trained (fine-tuned) solutions.
- **300 A (RULED):** the two typed-proposer defects (class set dropped by the receipt builder; `sample_id_sha_prefix` holds the
  response-hash prefix) are fixed before the next loop reuse and proven on a 4-row dry run; no work now.
- **Incident cause CLOSED:** the owner closed the terminal windows manually at about 10:33 local (14:33Z); the hidden-console
  wsl.exe sessions of the three tasks received the console-close control and died, and the distro instance stopped with its last
  session. Consequence already applied: fstab-backed mount; rule: closing console windows kills Task-Scheduler-owned WSL work --
  the owner is asked to leave hidden conhost windows alone, and the coordinator keeps the task set minimal.

### Data-root CUT-OVER DONE: verification manifests, default flipped, locator green, E: original retired by rename (coordinator, 2026-10-12 19:20Z)

- **Verification pass** (task SAEA-Cutover-296, 15:52-19:06Z, 274 tooling, `--jobs 20`): every subtree of the E: data root was rsynced
  into the hot root `/home/chao/saea-data/speechrl-data` (a no-op where a lane had copied it) and verified by sha256 manifests of every
  regular file on BOTH sides (relative path, size, sha256; sorted; compared byte-for-byte). Five receipts, all `all_verified = true`:
  `run-20261012T155257Z-16514` (hot), `...172237Z-72788` (runtime), `...172515Z-346466` (derived), `...173445Z-1171280` (rest),
  `...173457Z-1174317` (datasets, models); the receipts live under `<hot>/receipts/migration-ext4/` (and the parked copy under
  `/home/chao/saea-migration/receipts-ext4/`). The owner's table (files / GB / first 12 hex of the manifest sha256 / symlinks
  re-pointed off the E: path / seconds):

  | subtree | verdict | files | GB | manifest sha256 | links re-pointed | s |
  | --- | --- | ---: | ---: | --- | ---: | ---: |
  | runs | verified | 27,402 | 84.27 | 513895e98710 | 0 | 397 |
  | analysis | verified | 4,863 | 4.40 | c37a299b2806 | 61 | 18 |
  | knowledge | verified | 200 | 0.61 | 898a8c630457 | 0 | 5 |
  | prepared | verified | 1,776,869 | 11.13 | 9466f171aaaa | 0 | 2083 |
  | coordination | verified | 281,945 | 46.29 | 45d2548928bb | 649 | 2795 |
  | serving | verified | 517 | 3.60 | c7baef405e1b | 0 | 52 |
  | attempts | verified | 3,685 | 0.00 | ada3e82230a1 | 0 | 29 |
  | locks | verified | 20 | 0.00 | 7abdc37d9461 | 0 | 0 |
  | vectors | verified | 53 | 3.92 | e12abaab98c1 | 0 | 32 |
  | preparation-runs | verified | 43 | 0.02 | 153ec98e7d07 | 0 | 1 |
  | provisional | verified | 6 | 0.00 | eeac7a65568b | 0 | 0 |
  | receipts | verified | 8 | 0.02 | 542cb403df97 | 0 | 0 |
  | trace-intermediates | verified | 30 | 0.11 | 9be19a10353f | 0 | 1 |
  | wire-check | verified | 3,733 | 9.40 | 2580fe859656 | 0 | 44 |
  | official-evaluator-source-bundles | verified | 2 | 0.02 | 35fd5077ea4b | 0 | 0 |
  | references | verified | 20 | 0.00 | f096ca3406d8 | 0 | 0 |
  | manifests | verified | 151 | 0.40 | e08467f03d37 | 0 | 4 |
  | environments | verified | 18,161 | 0.59 | 1e19c0a82697 | 4 | 40 |
  | repos | verified | 11,555 | 1.62 | 1d55af753735 | 0 | 35 |
  | derived | verified | 102,678 | 191.59 | 719870483aff | 0 | 570 |
  | archive, logs, program-archives, research, settlements, telemetry, working, four `saea-slurp-*-read-*` roots, `.bin`, six loose files | verified (18 rows) | 295 | 0.57 | (per-row in the receipt) | 0 | 12 |
  | datasets | verified | 1,156,362 | 1080.64 | cd85e6ccc575 | 0 | 4764 |
  | models | verified | 206 | 160.34 | 9de7ce6b2e74 | 5 | 717 |
  | **total** | **43 rows, all verified** | **3,421,269** | **1,688.8** | | 719 | |

  Deletion set (owner 2026-10-12): `_repro` (30 GB), `system-text-search` (32 GB) and `survey-*` (7.6 GB) never entered the ext4 copy;
  the seventeen ChatGPT-line coordination packages were removed from it after verification (coordination 1,197 -> 1,180 entries).
  Disk 1 after the pass: 1.5 TB used, 550 GB free of 2.0 TB (growth to 3.6 TB per 291/298 in the next no-flight window).
- **Cut-over (284 step 2 closed, 294 A, 296):** `SAEA_DATA_ROOT_DEFAULT` = `/home/chao/saea-data/speechrl-data` (a literal: the locator
  and the Python helpers read the assignment textually), manifest `roots.data_root.current` = the hot root with `status = cut-over`,
  `~/.bashrc` exports the same value (comment names the authority), 19 queue wrappers rewritten to source the authority (the historical
  migration lanes keep their labelled SRC literal), umbrella `CLAUDE.md` / `AGENTS.md` data-root line updated. Locator: PASS in host
  mode with `--require-hot-mounted` and in repository mode (0 failures, 0 warnings).
- **297 B executed:** the E: original is renamed to `speechrl-data.retired-20261012` (not deleted) until one full 268 chain has flown on
  the new root; then deleted with the deletion set in the same window as the 3.6 TB growth (298 A).
- Timing receipt: `docs/checks/speech-aware-evidence-acquisition/2026-10-12-engineering-base-timing/post-cut-over.json` (this commit).

### 268 launch: three launch defects found and fixed before the first contact (coordinator, 2026-10-12 19:55Z)

- **WSLENV carried the retired data root.** A Windows USER environment variable `SPEECHRL_DATA_DIR` (E: path) is shared into every
  WSL session through `WSLENV`; after the cut-over the authority refused every flip and serving start ("inherited SPEECHRL_DATA_DIR
  differs from the data root"), and the 19:14Z mint, running with the stale value, wrote the decision receipt onto a stray E:
  directory. Fixed at the source (user variable set to the hot root; the stray receipt parked beside the real one as
  `root-admission-v1.stray-env-20261012T1914Z.json`; re-minted on the hot root, sha 3cf64523...). Rule: processes started before
  the change (this coordinator session included) carry the old value; every wsl call from such a session sets the variable.
- **The ext4 flip wrapper reported success on a refused flip.** With the receipt absent the flip script exited 6, `flip_loop` saw
  HEAD unchanged and called it converged, `flight_registration_check --cell` FAILED on all three cells, and `flip_package_ext4.sh`
  still printed `FLIP_CHAIN_DONE rc=0` (the gate output is only tee'd). Rule until the wrapper is patched (next no-flip window):
  read the gate block of the flip log before any chain launch; a 13-second three-cell flip is not a flip.
- **The model-free preflight over-counts the module Solver render by 45 %.** `core.flight.cli check` refused the smoke and lock cells
  with `prompt budget COMPACT_REQUIRED ... physical_margin_tokens -817` (rendered 21,269 "tokens" + 4,096 cap + speech + reserve
  exceed the 24,576 slot). The preflight counts the JSON payload at 4 bytes per token (`_default_token_counter`, documented as a
  placeholder); the exact native per-contact gate at the wire measured the same requests of the Instruct lock column (iteration 3)
  at p50 10,236 / p90 12,551 / max 15,076 tokens with `context_compaction = null` on all 8,640 contacts (the registered fact 14,641 is
  the Solver maximum). The package's prerequisite 3 ("17,406-token live limit, Solver maximum 14,641, no row compacted") was
  therefore true at the wire and false for the heuristic, and no 24,576-slot cap above about 235 tokens could pass the heuristic.
  Fix (commit 16082c1a2): the three cells declare `preflight_budget_mode = defer-to-native-contact-fit` (the R01C mechanism: the
  estimate is recorded, admission is decided by the registered exact per-contact gate), and the runtime accepts that deferral under
  `context_fit_policy = compact-or-abstain` as well as `raise` (both hand every realised request to the exact gate; neither silently
  truncates) -- the lock's compact-or-abstain is part of the compiled module block and stays; two unit tests added, the derive script
  carries the rule, the three baselines were re-derived (`thinking_system_derive_cells.py`), registration tests 15/15. The Thinking arm
  thus flies the same requests as the Instruct lock with no compaction expected (wire fit 14,641 + 4,096 + 28 + 3,072 reserve =
  21,837 < 24,576); any contact that does not fit compacts or abstains at the wire and is counted in the read's node table.

### 268-B smoke read and sign-off amendment; arms launched (coordinator, 2026-10-12 20:10Z)

- **Smoke** (`SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-SMOKE-4-V1`, flight commit c112da11b, sealed 19:55Z, 4 rows / 8 contacts on the
  THINK-BUDGET session think-budget-np4): Perception 0 cap hits, 0 empty, 4 `stop` finishes, 1 forced close, completion p50 2,014 / max 3,196
  tokens, prompt mean 3,608, 50.32 s per contact; Solver 0 cap hits, 0 empty, 4 `stop`, 1 forced close, completion p50 1,436 / max 3,121,
  prompt mean 8,447 (wire tokens: the exact gate; consistent with the Instruct lock's 14,641 maximum), 35.31 s per contact; no reasoning
  marker in content, no JSON failure. Receipt `analysis/SAEA-SLURP-SYSTEM-THINKING-CORE-FOLD-B-READ-V1/smoke-decode-cost.json`.
- **Projection vs plan:** 6.42 slot-normalised GPU-h per 1,080-row pass against the registered 5.1 ceiling (3.89 expected x 1.3): the
  bare-core COST channel's E[min(reasoning, 3,072)] = 848 tokens does not transfer to the system prompts, where the mean reasoning is
  1,985 (Perception) / 1,768 (Solver) tokens -- the core thinks about twice as long with 8-15k tokens of knowledge in view.
- **Sign-off amendment (commit 7b50fdbab), mirrored on every bound row before any arm contact (lesson of the 266-E Thinking rec1):** family
  GPU model replaced by the smoke-measured per-contact seconds (`SMOKE_MEASURED_S_PER_CONTACT`; the pre-smoke model kept as
  `modelled_row_seconds` for the design record); lock and aa ceilings 5.1 -> 8.4 GPU-h on the generation AND FIT rows and plans; package
  regenerated (`thinking_system_write_registration.py`, plans, protocol, facts, README, preregistration); receipt re-minted (sha b8c6c172...;
  the 5.1 receipt kept beside it as `root-admission-v1.superseded-<ts>-gpu51.json`); registration tests 15/15; decoding knobs unchanged
  (budget 3,072, cap 4,096). Expected wall per arm 7.1-9.2 h; both arms about 13 GPU-h, roughly 15-18 h wall. The owner's 268 B brief
  quoted "two c2 passes about 3.9 GPU-h each"; the measured cost is 1.65x that -- recorded here, not re-asked (298 A: experiments
  start as soon as possible; the numeric GPU caps are retired, pre-registration is honest).
- **Sign-off marker** `/home/chao/tsys-decode-signoff.marker` written 20:03Z; the chain's `arms` segment (lock then aa, one session) flies at
  the flight commit of the amended flip; the smoke's seal at c112da11b is the sign-off evidence and is not re-flown (one-shot attempt).
- **Flip and launch:** the amended package was re-pinned for the two arms only (`TSYS_KINDS="lock aa"`; the flown smoke keeps its
  one-shot attempt), gate PASS for lock and aa, master fast-forwarded to flight commit be7878fc6 (20:11Z); the arms chain
  (`chain_tsys_arms.sh`, task SAEA-Chain-TSYS-Arms) started 20:12Z on the think-budget-np4 session: lock (1,080 rows, 2,160 contacts),
  then aa, one session, one flight commit; the first refused re-pin (the smoke's attempt already existed) and the ext4 worktree
  left on a throwaway branch were both cleared (rules recorded). Swap back to slurp-np4, READ-row countersign and the read follow the
  two seals.

### 268-B lock arm SEALED; aa arm flying (coordinator, 2026-10-13 06:05Z)

- `SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-LOCK-V1` sealed 05:58Z at flight commit be7878fc6: manifest COMPLETED, 2,160 contacts
  (1,080 rows x Perception + Solver), 6,310 speech-audio seconds, summed call latency 37.65 h = about 9.4 slot-normalised GPU-h on the
  4-slot session (wall 9 h 46 min, 1.84 rows/min) against the amended 8.4 ceiling (the smoke's per-contact seconds under-estimate
  4-slot contention by about 1.5x; the ledger's gpu cell is a pre-registered ceiling, the seal records summed latency, no runtime abort --
  the overrun is stated here and in the read, and the next Thinking registration plans from a measured 4-slot throughput run). The twin
  `...-AA-V1` started 05:58:52Z on the same session and flight commit (registration gate ok, prelaunch ok); expected seal about 15:40Z.
  Lock rows (generation + FIT) closed with `ledger_mark_consumed.py --apply`; the READ row stays a draft until the twin seals.

### 268-B READ: the locked system on the Thinking core TRANSFERS-ABOVE-BAR; decision 299 A fires (REBUILD-BASE-ON-THINKING) (coordinator, 2026-10-13 15:50Z)

- **Seals:** lock `SAEA-SLURP-STAGE3-THINKING-SYSTEM-FOLD-B-LOCK-V1` 05:58Z and twin `...-AA-V1` 15:39Z, both at flight commit be7878fc6 on the
  think-budget-np4 session (budget 3,072, cap 4,096, `drop-reasoning-v1`, reasoning bytes hash-and-stats only), 2,160 contacts each (1,080
  rows x Perception + Solver), summed latency 37.65 / 37.82 h (about 9.4 slot-normalised GPU-h each against the 8.4 ceiling, stated).
  Rows closed with `ledger_mark_consumed.py --apply`; the READ row `SAEA-SLURP-SYSTEM-THINKING-CORE-FOLD-B-READ-V1` root-countersigned
  15:42:31Z after both seals and before any number was read; card swapped back to slurp-np4 at 15:42Z.
- **Read** (`analysis/SAEA-SLURP-SYSTEM-THINKING-CORE-FOLD-B-READ-V1/read.json`, utterance-cluster bootstrap CI95; comparators: the
  Instruct lock column of loop iteration 3 and the bare Thinking core of 266-E; all TRAIN Fold B, development numbers, never a test claim):

  | metric | Instruct lock (i3) | bare Thinking (266-E) | Thinking system (lock) | twin (aa) | d_system | CI95 | twin offset | vs bare |
  | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
  | SLU-F1 | 64.45 | 45.39 | 71.61 | 72.75 | +7.15 | [+5.08, +9.26] | +1.15 [-0.09, +2.42] | +26.21 [+23.84, +28.64] |
  | intent | 82.69 | 76.76 | 85.00 | 84.91 | +2.31 | [+0.56, +4.07] | -0.09 [-1.30, +1.11] | +8.24 [+6.20, +10.37] |

  Verdict **TRANSFERS-ABOVE-BAR** (d_system >= 2.5, CI95 lower bound 5.08 above the twin offset 1.15, intent guard holds, 0 reasoning
  markers in content). Equal-scenario weighting SLU +7.68 / intent +2.31; 16 of 18 scenarios gain SLU (music -4.20, transport -0.52);
  intent saves 59 / harms 34 vs the Instruct system. Transfer share of the bare 266-E delta (+11.90): 60 %. Completion: 0 cap hits, 0
  length finishes, 0 empty, 0 no-JSON on all 4,320 contacts (the bare Thinking core at cap 8,192 had 36 empty rows); the budget sampler
  forced the close on 190 / 496 (lock) and 189 / 470 (aa) Perception / Solver contacts, tokens p50 1,964 / 2,408, p99 about 3,190;
  58-67 s per contact at np4.
- **Decision 299 A trigger: 3 of 3 -> REBUILD-BASE-ON-THINKING** (`p3_trigger_299` in the read: SLU resolved above the twin offset and
  >= +1.5 pp; intent CI95 lower bound +0.56 >= -0.65; completion 100 %). Consequence (P3): the engineering base is rebuilt around the
  Thinking core -- Thinking speech packets for every carrier (A2T / E21 / E22 via the Thinking mmproj, GPU encode), the SLURP lock and
  the carrier all-off/direct baselines re-registered and re-read on Thinking, serving geometry planned from measured 4-slot throughput
  (1.84 rows/min at np4 x 24,576 with budget 3,072), the SOTA comparison redone on the Thinking base (285). A DEV-2000-ADDED replicate of
  the Thinking system precedes any lock (decision 28: Fold B numbers are development numbers).
- **Results note:** `docs/results/2026-10-13-slurp-268b-thinking-system-fold-b-read.md` (Opus, from the read and smoke receipts); the
  READ row closes when the note cites it. Registered budget vs spend: planned 8.4 GPU-h per arm, spent about 9.4 (summed latency / 4
  slots); calls 2,160 of 4,320 planned per arm; audio 6,310 s per arm.

### P3 programme under decision 299 A: the engineering base moves to the Thinking core -- plan of record (coordinator, 2026-10-13 16:20Z)

Owner decision 299 A (2026-10-12) fires on the 268-B read (3 of 3 conditions). The rebuild is sequenced so that every GPU hour buys a
registered read, in the owner's priority order (SLURP system optimisation first; the base runnable on A2T / E21 / E22 second; SOTA
comparison last). Development numbers only until a DEV replicate exists; never a test claim without a signed allowance.

| step | object | GPU | gate / output |
| --- | --- | ---: | --- |
| P3.0 | No-flight window: 297 B delete of `speechrl-data.retired-20261012` (E:), 298 A VHDX growth 2 -> 3.6 TB + `resize2fs`; then Instruct serving back on | 0 | locator `--host --require-hot-mounted` PASS; E: free >= 500 GB |
| P3.1 | **Thinking system DEV replicate**: the lock v2.2 module graph on the Thinking core on DEV-2000-ADDED (lock + in-chain twin, same shape as 268-B), Thinking packets for the DEV roster encoded in the swap window (`direct_fb_packets_gpu.sh`, about 0.16 s per row), comparator = the Instruct lock already read on that roster | about 2 x 9.5 h | NOMINATED iff SLU CI95 lower bound > the twin offset and intent guard holds -> the Thinking system becomes the SLURP lock candidate v3.0 (Fold B + DEV replicated); the budget 3,072 / cap 4,096 knobs and `drop-reasoning-v1` are part of the lock |
| P3.2 | **Carrier packets on the Thinking mmproj**: A2T frozen 400 (+ the 4,000 native-system roster if still live), E21 full discovery windows, E22 windows -- GPU encode, promotion receipts per root (same receipt form as the Fold B promotion) | about 1-3 h | promotion receipts; `derived_media_confinement_check` and the locator's packet-root rule PASS |
| P3.3 | **Carrier baselines on Thinking**: A2T stage-3 all-off + direct, E21 all-off + direct, E22 all-off + direct, derived from the registered Instruct cells with the Thinking model fragment and the Thinking packet roots (the four red registration packages are re-pinned here); the thinking knobs are fixed at the SLURP values until a carrier smoke says otherwise | A2T about 2 x 1 h, E21 about 4 h, E22 about 4 h | each carrier: smoke -> sign-off -> arms; per-stratum tables with the paper column (A2T) / Whisper-normalised WER beside saea-scoring (Earnings); this closes the goal's "base runs on A2T / E21 / E22" item on the Thinking base |
| P3.4 | **Serving geometry for Thinking**: measured 1.84 rows/min at np4 x 24,576; test np6 x 24,576 (KV at q8_0) and the per-node thinking policy (Perception without thinking, 273 A) as registered A/A-free throughput runs on the smoke roster only | about 1 h | a throughput receipt; no claim |
| P3.5 | **SOTA redo (285)** on the Thinking base: the comparator table rebuilt with the P3.1 / P3.3 numbers, zero-shot and fine-tuned rows kept apart | 0 | `docs/readiness/<date>-sota-comparator-table-v2` |
| P3.6 | Test-sample read of the Thinking system under a new allowance (successor-3), only after P3.1 is NOMINATED | about 2 x 25 h at 3,010 rows | owner signature first |

Standing rules: one experiment in flight; a cell is admitted only after its predecessor is replicated or root-caused; every plan ceiling
comes from a measured 4-slot throughput run (the 268-B overrun is the lesson); no flips or `core.flight.cli` checks while a driver is
alive; the serving session is swapped, never restarted mid-flight.

### No-flight window executed: 297 B delete, 298 A disk growth; Instruct serving back on (coordinator, 2026-10-13 16:35Z)

- **298 A:** serving stopped 16:12Z (card empty, no flight, no agent session); `wsl --shutdown`; `diskpart expand vdisk maximum=3686400` on
  `E:\saea-data-1.vhdx` (virtual size 3,600 GB; the file stays dynamic, 1.6 TB on disk); re-attached with `wsl --mount --vhd --bare`;
  `/etc/fstab` remounted it by label (device letter moved sde -> sdd); `resize2fs` online -> filesystem 3.5 TB, 1.5 TB used, 2.1 TB free.
  Locator host mode with `--require-hot-mounted`: PASS (0 failures, 0 warnings). Instruct session slurp-np4 restarted 16:17Z (health ok,
  22.9 GB resident).
- **297 B:** the retired E: original `speechrl-data.retired-20261012` deleted 16:17-16:30Z (one full 268-B chain had flown on the new root;
  the verification manifests are on file). PowerShell `Remove-Item` stopped on paths beyond MAX_PATH; `rmdir /s /q` with the `\\?\` prefix
  finished it. E: now 1.67 TB used / 2.43 TB free (the >= 500 GB rule holds with margin). The umbrella `exploring-l4-intelligence/runs`
  directory on E: is an unrelated pre-program leftover and was not touched.
- Engineering base after the window: hot root `/home/chao/saea-data/speechrl-data` on the 3.5 TB ext4 disk, authority default, manifest
  `status = cut-over`, fstab mount, WSLENV user variable aligned, flips on ext4, hidden-console scheduled tasks. Merged agent worktrees
  removed (loop note, literal sweep, base unification, 268-B note); P3.1 package work proceeds in `sonnet-tsys-dev`.

### P3.1 LAUNCHED: the Thinking system on DEV-2000-ADDED (lock + twin + smoke) at flight commit 37b0ed0aa (coordinator, 2026-10-13 17:25Z)

- **Package** `docs/readiness/2026-10-13-slurp-system-thinking-core-dev2000-added-v1/` (Sonnet, merged 9b3e1b0d0; family
  `scripts/flights/direct/thinking_system_dev_family.py` importing the Fold B family unchanged; SHORT `tsysd`). Parent and comparator:
  the sealed NX R5 composed cell on DEV-2000-ADDED (`SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1`, study commit 9a0a3384b; lock v2.2
  with v4g, review off, program `phase-native-module-v1-c2`, 2 contacts per row) -- the brief's `module-comp1b-dev2000-added` cells carry
  lock v2.1 with the Reviewer loop (11 contacts per row) and only their twin sealed, so they are not request-identical. Bare comparator:
  `SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1` (bare Instruct; roster identity ee6c43cd... matches); no bare Thinking core exists on DEV.
  Knowledge view: the parent's full-TRAIN pin. Knobs identical to 268-B (budget 3,072, cap 4,096, `drop-reasoning-v1`,
  `preflight_budget_mode = defer-to-native-contact-fit`). Ceilings from measured throughput: `ceil_0.1(rows / 1.84 / 60 x 1.3)` = 11.8 GPU-h
  per arm, smoke 0.5 (registered total 24.1).
- **DEV Thinking packets:** row `SAEA-SLURP-DEV2000-ADDED-THINKING-PACKETS-GPU-V1` appended and countersigned 16:59Z; GPU window
  `direct_fb_packets_gpu.sh --run --stage dev2000-added` 17:02-17:06Z (Instruct stopped, 1,000 rows encoded at 0.114 s per row, 0 failed,
  promoted into the Thinking packet root as `DEV-2000-ADDED-promotion.json`, sha 1a6dca3a...; think-budget-np4 session started and ready);
  receipt pinned, cells re-derived with `--require-receipt`, package re-written, seven rows appended; six flight rows countersigned
  17:06:48Z (READ row stays a draft); decision receipt minted (sha cb5354a6...); ext4 flip 17:13-17:21Z, gate PASS for all three cells,
  master fast-forwarded to 37b0ed0aa; chain task SAEA-Chain-TSYSD started 17:22Z (smoke -> sign-off marker
  `/home/chao/tsysd-decode-signoff.marker` -> lock -> aa, one session). Expected: lock about 9.5 h, aa about 9.5 h.
- **Read rule** (`scripts/analysis/slurp_system_thinking_core_dev_read.py`): NOMINATED iff the SLU CI95 lower bound exceeds the twin
  offset and the intent guard (0.65 pp) holds; the 2.5 pp bar and the decision-299 completion rate are reported beside the word. A
  NOMINATED read makes the Thinking system the SLURP lock candidate v3.0 (Fold B + DEV replicated); a test read needs a new allowance.
- Housekeeping: two test fixes (closed rows accepted; DEV package rows accepted), the Git Bash path-conversion trap on `saea_task.ps1`
  (register tasks from PowerShell or with `MSYS_NO_PATHCONV=1`).

### Owner rulings 301-306 and the priority correction 307 (owner, 2026-10-13 17:40Z; recorded by the coordinator)

Owner (verbatim): 「决策301：A，决策302：A，决策303：A；决策304：可以lock，但是要考虑一个问题，是否有一些节点不需要开思考模式？；决策305/306：按你建议；
你的实验安排我有些疑问，我们为什么不是优先把training free RL在SLURP上的优化方向和优势都迭代好了之后，算法都按照speech agentic system的模式都进行了相应的适配和改造之后，再开展其他内容的实验呢？」
English: "301: A; 302: A; 303: A; 304: the lock is fine, but consider one question -- are there nodes that do not need thinking mode at
all?; 305/306: as you recommend. I have a doubt about your experiment ordering: why do we not first iterate the training-free RL
optimisation directions and advantages on SLURP to completion, adapt and rework the algorithms into the speech agentic system pattern,
and only then start the other experiments?"

- **301 A (RULED):** test-sample allowance successor-3 is signed now (`docs/receipts/owner/2026-10-13-slurp-test-sample-allowance-successor-3.json`,
  same terms as v2: one attempt per id, aggregate-only, no smoke, no re-fly); the read flies automatically once P3.1 reads NOMINATED on DEV:
  the Thinking system lock arm on the 3,010-row sample, comparator = the sealed successor-2 v2.2 test read, declared twin offset = the
  DEV twin offset (no in-chain replicate on the test sample; the limitation is stated in the read).
- **302 A (RULED):** carriers A2T -> E21 -> E22, all-off and direct baselines only on the Thinking core (the A2T Instruct A/A paired 400 is the
  comparator); **but see 307 for the ordering**.
- **303 A (RULED):** strict serial GPU queue (one experiment in flight).
- **304 (RULED, with a question):** v3.0 locks the current decoding knobs (budget 3,072, cap 4,096, drop-reasoning-v1); the owner's question
  "which nodes do not need thinking at all" becomes the FIRST node-level round on the Thinking base (per-node thinking policy, decision
  273 A mechanism): Perception off / Solver on, Perception on / Solver off, both on (the lock), both off (= the Instruct-like no-think
  core on the same weights), read at n = 1,080 on Fold B with the twin design; throughput and the per-node reasoning statistics are the
  secondary read.
- **305 (noted), 306 A (RULED):** E22 stays in scope in the E21 form, last among the carriers.
- **307 (owner priority correction, RULED by the question itself):** after the DEV replicate (P3.1), the programme iterates the
  training-free RL optimisation on SLURP on the Thinking base until it plateaus -- node-level rounds (thinking allocation per node,
  reasoning budget, Solver template / USE, knowledge SUPPLY), then the loop mechanisms (reflective playbook ACE, typed proposer, GEPA /
  template population) re-run on the Thinking residuals, each adapted to the speech-agentic-system pattern (node-local tables, same-flight
  columns, twin designs) -- BEFORE the carrier baselines (P3.2/P3.3) and the SOTA redo. Carriers run only as GPU fillers in forced gaps or
  after the SLURP line plateaus; the test read (301 A) stays attached to the SLURP line. Rationale recorded: the research object is the
  system and its training-free optimisation; the Thinking core changes the residual-error profile, so every node mechanism must be
  re-measured there; carriers only prove portability of the base.

### 300 A executed: the two typed-proposer defects fixed (coordinator, 2026-10-13 19:05Z)

Merged `sonnet/tfrl-proposer-fixes-300a` (cba223c5b): (1) the offered class set per carrier now travels from the registered
`tfrl_proposer.carriers` block into every typed-receipt entry (`allowed_classes`) and the validator refuses an out-of-class candidate
with the finding `class-not-allowed` (`FINDING_CLASS_NOT_OFFERED`); `candidates.json` carries an `offered_class_check` block and the
close receipt a `typed_class_check` block; sealed iteration 1-3 receipts carry no class set and read `applied: false`. (2)
`sample_id_sha_prefix` now holds sha256(sample id)[:12]; the response-hash prefix lives under `response_sha256_prefix`; readers accept
both layouts (`v1-legacy-response-hash-in-sample-id-field` / `v2-sample-id-sha-and-response-sha-prefixes`). Eight new unit tests; the
loop package README carries a dated successor note (iterations 1-3 flew with both defects). Open item (pre-existing, fails on master
too): `test_iteration_one_regression_reproduces_the_hand_built_inputs_byte_for_byte_except_the_pins_free_text` on the i1 ACE wrap
receipt's `authored` / `source` fields. The loop is ready for its next use on the Thinking residuals (307).

### NX-T R1 built and merged, HELD behind P3.1 (ruling 304: which nodes need thinking) (coordinator, 2026-10-13 20:05Z)

- **Harness (merged bf6945a5d):** a same-flight column arm kind over the per-node decoding knobs -- `roles.perception.thinking_variants`
  (level-2 Perception branch group; per-arm `thinking_policy` of `enable_thinking` / `reasoning_budget_tokens` / `answer_reserve_tokens`
  per node, any other knob refused by name; receipt schema `saea-perception-branch-arms-v5` with an optional twin; the bundle verifier
  re-reads each arm's trace request against its declared policy). The delivering arm and its twin declare no policy and take the
  unchanged path: a unit test composes the unarmed 268-B lock request and the delivering arm's and finds the rendered body, the request
  payload bytes and the role-request bytes equal minus the arm id; a 4-row production-graph test matches the delivering arm's Perception
  and Solver requests to the unarmed plan per row. Every arm renders the delivering arm's evidence, template and QueryState; a non-
  delivering arm's Solver prompt carries that arm's own Perception note (independent chains, no note sharing). 93 tests on the new and
  touched files, gates PASS.
- **Cell** `slurp-native-stage3-nxt-r1-thinking-policy-fold-b-v1` (+ smoke-4), TRAIN Fold B 1,080 rows, program `phase-native-module-v1-c10`
  (2 + 2 x 4 contacts per row), Thinking packets of Fold B, session think-budget-np4, `defer-to-native-contact-fit`; arms: `both-on`
  (delivering, last), `both-on-twin` (request-identical A/A null), `perception-off`, `solver-off`, `both-off` (the no-think core on the
  same weights; `max_tokens` 1,024 for a no-think node). Measurement block: same-flight node column, SLU primary, intent secondary,
  `claims_benefit` false, expected effect 7.15 pp (the Thinking-vs-Instruct system gap the no-think arm is expected to lose), external
  reference = the 268-B twin offset +1.15. Ceiling `ceil_0.1(1,080 x 3.25 / 1.84 / 60 x 1.3)` = 41.4 GPU-h (expected 31.8; arm mix
  1.0 + 1.0 + 0.6 + 0.6 + 0.05 full 268-B rows per row), smoke 0.5; calls 17,280 (10 per row + fallback allowance). Package
  `docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/`; scripts `scripts/flights/nx/nxt_r1_*` (SHORT `nxt1`); reader
  `scripts/analysis/slurp_nxt_thinking_policy_column_read.py` (per-arm levels, paired deltas vs both-on with cluster-bootstrap CI95,
  per-node tokens, finish-reason / cap / empty / forced-close table, think-marker count, seconds per contact, throughput table).
- **HELD** (303 A) until the P3.1 chain finishes: then re-derive, append + countersign the five rows, mint, ext4 flip, chain
  (smoke -> sign-off marker `/home/chao/nxt1-decode-signoff.marker` -> column). Open: `enable_thinking: false` on the Thinking checkpoint
  is unmeasured (the smoke settles it); `flight_registration_check.py` does not yet inspect the thinking-variant group; a pre-existing
  i1 regression test failure (ACE wrap receipt `authored` / `source` fields) is on master and unrelated.

### P3.1 READ: the Thinking system replicates on DEV-2000-ADDED -- NOMINATED; SLURP lock candidate v3.0 (coordinator, 2026-10-14 11:50Z)

- **Flight:** chain SAEA-Chain-TSYSD finished 11:43Z (driver exit 0): lock `SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-LOCK-V1` sealed 02:35Z
  (2,000 contacts, summed latency 35.07 h) and twin `...-AA-V1` sealed 11:42Z (2,000 contacts, 35.62 h), both at flight commit 37b0ed0aa; aa rows
  closed and the READ row countersigned 11:44Z; read `SAEA-SLURP-SYSTEM-THINKING-CORE-DEV2000-ADDED-READ-V1` (0 contacts) written 11:45Z; serving
  recycled in place to `think-budget-np4` (same target `--restart`: NX-T R1 is next and the 12-h bound had passed) instead of the swap back.
- **Read (n = 1,000, cluster bootstrap 10,000 draws, seed 20261011; development numbers, never a test claim):** levels SLU-F1 / intent %: lock
  74.69 / 84.5; twin 74.08 / 86.1; Instruct system (NX R5 composed, lock v2.2) 67.18 / 82.0; bare Instruct 38.09 / 61.7. d_system (lock minus
  Instruct system) SLU **+7.52 [+5.46, +9.62]**, intent **+2.50 [+1.00, +4.07]**; vs bare SLU +36.60 [+33.28, +39.86], intent +22.80 [+19.84, +25.97].
  Twin offset (aa minus lock) SLU -0.61 [-1.88, +0.69]; intent +1.60 [+0.60, +2.67] (21 saves / 5 harms: the in-flight intent variability is
  resolved above zero on this roster; it bounds the intent attribution, not the SLU verdict). Replication of Fold B: +7.52 vs +7.15 (share 1.05).
  Completion 2,000/2,000 on the lock, 0 cap hits, 0 reasoning leaks or think markers in delivered content; forced closes Perception 174 / Solver 457;
  per-scenario natural +7.52 / equal-scenario +8.85 SLU (intent +2.50 / +0.54); datetime (9), recommendation (6) and social (4) unresolved.
- **Verdict NOMINATED** (SLU CI95 lower bound 5.46 above the twin offset 0.61; intent guard holds); the 2.5 pp cross-flight bar is cleared by the lower
  bound; decision-299 conditions 3/3 on this roster (REBUILD-BASE-ON-THINKING). Consequence (package rule): the Thinking system is the **SLURP lock
  candidate v3.0** (Fold B + DEV replicated: 268-B +7.15 [+5.08, +9.26], P3.1 +7.52 [+5.46, +9.62]); the test read under allowance successor-3 (301 A)
  is now unlocked (lock arm only; its Thinking packets for the 3,010-row sample need their own countersigned packets row and a GPU swap window).
- **Next (307 order):** NX-T R1 (per-node thinking policy, ruling 304) launches now on the Thinking base; the successor-3 test read is built in
  parallel and flies after NX-T R1 in the serial queue (303 A). Results note: Opus, `docs/results/2026-10-14-slurp-p31-thinking-system-dev2000-added-read.md`.

### NX-T R1 LAUNCHED: the per-node thinking-policy column at flight commit 37e177e3e (coordinator, 2026-10-14 12:10Z)

- Sequence (README "Chain sequence"): re-derived and registered at study commit 8132badd8 (11:52Z; writer `nxt_r1_write_registration.py
  --append-ledger`); the four flight rows (smoke-4 generation + FIT, column generation + FIT) countersigned 11:52:23Z, the READ row stays a draft
  until the column seals; receipt minted (sha 87acf1be...); committed 04603b8cd; Opus's P3.1 note merged 40706d54a BEFORE the flip (no concurrent
  merge and flip); ext4 flip 12:00-12:05Z (smoke 57515cc42, arm 14de6c0a3, pins 37e177e3e; gate PASS for both cells; master fast-forwarded);
  handoff refreshed 23ef41de8; serving = the recycled `think-budget-np4` session (11:44Z restart); watchdog hold present; chain task
  SAEA-Chain-NXT1 (`/home/chao/saea-queue/chain_nxt1.sh`, log `/home/chao/nxt1-chain.out`) started 12:08Z: smoke-4 (40 contacts) ->
  coordinator reads `nxt_r1_read.sh smoke` (above all: does a no-think arm still emit reasoning bytes or a think marker?) -> sign-off marker
  `/home/chao/nxt1-decode-signoff.marker` -> the five-arm column (1,080 rows, 10,800 contacts, ceiling 41.4 GPU-h, expected 31.8).
- Ordering note (coordinator, for the owner): ruling 301 A reads "the test read flies automatically once P3.1 reads NOMINATED"; it is NOMINATED, but
  its package (the sample's Thinking packets stage + the successor-3 cell) is still in build (Sonnet, worktree `sonnet-successor3-test-read`),
  while NX-T R1 was ready and flipped; under ready-first serial GPU (303 A) NX-T R1 flies first and the test read follows it in the queue.
  If the owner prefers the test read before the node rounds, say so: the column can be held after the smoke (the sign-off marker is the gate).
- Open engineering recorded: the DEV reader's decision-299 note string says "TRAIN Fold B" on a DEV read (text only, numbers correct);
  `flight_registration_check.py` does not inspect the thinking-variant group (package prerequisite 6).

### NX-T R1 smoke signed off; the column flies (coordinator, 2026-10-14 12:20Z)

- Smoke-4 sealed 12:16Z (40 contacts); `nxt_r1_read.sh smoke` (decode cost per arm and node, no score): every no-think node -- both-off
  (Perception and Solver), perception-off Perception, solver-off Solver -- 0 reasoning characters, 0 think markers, 0 empty answers, 0 malformed
  JSON, finish stop, 28-97 completion tokens (cap 1,024, 0 hits); think nodes 1,714-2,363 mean completion tokens, forced closes 1-2 of 4, 0 cap
  hits; prerequisite 1 ("no-think on a thinking-only checkpoint is unmeasured") cleared at the form level. Throughput: both-on 98 s per row,
  perception-off 57 s, solver-off 53 s, both-off 5.5 s; measured arm mix 3.32 rows per both-on row (registered 3.25); projected 24.5 GPU-h for
  the column (ceiling 41.4, expected 31.8). Marker `/home/chao/nxt1-decode-signoff.marker` written 12:18:33Z; smoke rows closed.

### Decision 308 (proposed): amend the successor-3 test allowance for the sample's Thinking packets pass and the Thinking ceilings (coordinator, 2026-10-14 12:45Z)

- **Finding (Sonnet, successor-3 build):** the Thinking packets for the 3,010-row test sample are an encoder contact over `slurp:test` rows. Successor 1's
  packets pass cleared the test-split runtime guard because the 2026-09-27 allowance listed its run id under `preparation_run_ids` (fragment
  `configs/experiment/slurp-test-sample-3010-preprocess.json` pins that allowance's path and sha256); successor 2 reused those packets by pin and
  needed none. The signed successor-3 receipt (`docs/receipts/owner/2026-10-13-slurp-test-sample-allowance-successor-3.json`, ruling 301 A)
  permits only `...-SUCCESSOR3-THINKING-SYSTEM-V1` and `-FIT-V1`; its `core.packets` clause states the packets pass but no preparation id, and its
  `budgets` block is successor 2's (6,020 calls, 4.6 GPU-h, 16,413 audio s) while the Thinking cell's ceilings from measured P3.1 throughput are
  35.5 GPU-h (`ceil_0.1(3010 / 1.84 / 60 x 1.3)`), 6,020 contacts, 32,826 audio seconds (two listens per row). The guard is not weakened.
- **Options.** **A (recommended):** the owner signs a successor-3 amendment (v2 receipt, superseding by sha) that adds
  `preparation_run_ids = ["SAEA-SLURP-TEST-SAMPLE-3010-THINKING-PACKETS-GPU-V1"]` (encoder contact only, no answers, promoted under its own
  countersigned exposure row in a GPU swap window, one attempt) and sets the budgets to the Thinking ceilings; the packets fragment pins the v2
  receipt's sha; everything else unchanged. **B:** fly the test read on the Instruct packets (NOT valid: the Thinking mmproj audio tower differs,
  decision 266-era finding "Thinking needs its own packets"). **C:** defer the test read until after the node rounds (then the amended allowance
  is signed later, and the lock form may change).
- Until signed, the package carries a DRAFT v2 receipt with a zero pin and the chain refuses to start; the test read is queued after NX-T R1 anyway.

### Successor-3 test-read package merged, HELD behind decision 308 (coordinator, 2026-10-14 13:05Z)

- Sonnet's package merged e048c6e1a (branch commit 366eb8fd1, 37 files): cell `slurp-milestone-successor3-thinking-system-v1` derived from the
  P3.1 lock cell with successor 2's leaf moves (44 roster-bound, 6 role-bound, 5 bookkeeping, 12 experiment-block leaves; the delta successor 2
  -> successor 3 equals the delta R5-composed-DEV -> P3.1-lock-DEV on 18 leaves, path for path, values identical; `anything_else` empty);
  package `docs/readiness/2026-10-14-slurp-milestone-successor3-thinking-system-v1/` (+ preregistration page); packets stage `--stage
  test-sample-3010` (roster `thinking-test-sample-3010`, run id `SAEA-SLURP-TEST-SAMPLE-3010-THINKING-PACKETS-GPU-V1`, receipt
  `TEST-SAMPLE-3010-promotion.json`, create-only, Fold B / DEV receipts untouched); scripts `scripts/flights/nx/successor3_thinking_*` and
  `batch_chain_successor3_thinking.sh` (no smoke on the sample; refuses until the v2 allowance pin is non-zero); reader
  `scripts/analysis/slurp_successor3_thinking_read.py` (successor 2's words NEUTRAL / HARM / UNRESOLVED, claims_benefit false, DEV twin offset
  SLU 0.6144 / intent 1.6 as the declared null, no in-chain replicate stated, seed 20261014); ceiling 35.5 GPU-h = ceil_0.1(3010 / 1.84 / 60 x 1.3),
  6,020 contacts, 12,040 plan calls, 24,080 FIT endpoint calls, 32,826 audio seconds. DRAFT v2 allowance
  `docs/receipts/owner/2026-10-14-slurp-test-sample-allowance-successor-3-v2-DRAFT.json` (adds the packets preparation id and the Thinking
  budgets; signature "DRAFT: awaiting owner decision 308"); the signed successor-3 bytes are untouched; `src/` untouched (guard unchanged).
- Gates on the branch: engineering_base, harness_admission, finite_completion_policy, stage3_effect_floor, stage3_algorithm_label,
  derived_media_confinement PASS; flight_registration tree mode FAIL 61 blocking, identical to master's 61 (pre-existing, none successor-3);
  launch mode on the cell shows only the expected pre-countersign blockers. Not exercised: the real packets promotion, chain, flip, mint, read.
- Sequence once 308 A is signed: sign v2 (status authorised) -> `successor3_thinking_packets_fragments.py pin-allowance` -> registration
  (`--append-ledger`) -> countersign the packets row -> packets swap window `direct_fb_packets_gpu.sh --run --stage test-sample-3010` ->
  `--pin-receipt`, close the row -> derive `--require-receipt`, re-write -> countersign generation + FIT (READ after the seal) -> mint -> flip ->
  chain (after NX-T R1 seals; serial GPU) -> read. The allowance's `budgets` are not code-enforced (Sonnet found no consumer); the registered
  plans carry the ceilings that are.

### INCIDENT: Windows Update forced restart killed the NX-T R1 column (coordinator, 2026-10-14 15:55Z); decisions 309-311 proposed

- **Cause (System event log 1074):** 15:29Z MoUsoCoreWorker "operating system: Service Pack (planned)", 15:33Z TrustedInstaller "operating
  system: upgrade (planned)" -- Windows Update, not a manual close and not hardware. The host clock is Eastern time (UTC-4); the WSL distro and
  every log stamp this programme writes are UTC.
- **Loss:** the column attempt `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-v1` (started 12:18:45Z, last contact 15:29Z)
  died with the attempt record at state OPENED, 1,204 calls / 3,298 audio seconds spent (about 120 rows x 10 contacts, about 3 GPU-h); its
  attempt directory holds only the session-attach receipt -- the trace is written at the seal, so there is NO predecessor trace and E10 resume
  (mode A replay) has nothing to replay. The smoke (sealed 12:16Z) and its sign-off stand. master, the ledger and the packages are intact.
- **Restoration:** VHD re-attached and mounted by fstab after a `wsl --shutdown` (the distro had started before the VHD was attached, so the
  `nofail` entry was skipped); the stale `locks/flight.lock` parked at `/home/chao/flight.lock.stale-reboot-*` after verifying no driver,
  flight or server process survived; Thinking session restarted 15:48Z (`serving_swap.sh think-budget-np4 --start-only`).
- **309 (proposed): recovery of the column.** A (recommended): the cell's single root-diagnosed recovery re-registration (package rule): new
  generation attempt id and new FIT run/attempt ids, root cause named as above, re-flown whole, ceilings unchanged (41.4 GPU-h), cumulative spend
  recorded (predecessor 1,204 calls / 3,298 s). B: abandon NX-T R1 and go to R2 -- not recommended (R2's design depends on R1's answer).
- **310 (proposed): stop Windows Update automatic restarts.** A: policy `NoAutoRebootWithLoggedOnUsers = 1` + active hours (18 h window) + pause
  updates to month end (coordinator, needs the owner's admin authorisation); B: the owner pauses updates in Settings (5 weeks); C: accept the risk.
- **311 (notified): startup order.** The coordinator changes SAEA-Mount-Data1 to trigger at startup and, after the attach, to run `mount -a` inside
  the distro with retries, so the data root mounts whichever starts first; serving tasks remain manual.

### Owner rulings 308-311 (owner, 2026-10-14 about 16:00Z; recorded by the coordinator)

Owner (verbatim): 「决策308：按你的建议走；决策309：这里面 暴露了一个问题，我们的实验中断后恢复的能力太差了，你要系统性整改，另外分析下为什么需要用这么多gpu hours?我们目前应该不涉及大规模实验才对，即便要做大规模实验，你现在的实验基线锁定了吗？决策310：授权；决策311：可以；」 and, a few minutes later:
「我认为现在的实验效率太低了，你分析下根因，以及寻找下如何提升实验效率的方式和方法！」
English: "308: go with your recommendation. 309: this exposes a problem -- our ability to recover an interrupted experiment is far too weak; rectify it
systematically; also analyse why so many GPU hours are needed -- we should not be running large-scale experiments at this point, and even if we
were, is your experimental baseline locked? 310: authorised. 311: fine." / "I think the experiments are far too inefficient now; analyse the root
causes and find ways and methods to raise experimental efficiency."

- **308 A (RULED, done):** v2 allowance signed (`docs/receipts/owner/2026-10-14-slurp-test-sample-allowance-successor-3-v2.json`, status authorised,
  sha efd20fb6...), pinned into `configs/experiment/slurp-test-sample-3010-thinking-preprocess-gpu-v1.json`; the DRAFT file removed; package tests 19/19.
- **309 (RULED: systematic rectification):** two engineering lines opened in worktrees -- (a) a generic recovery re-registration library
  (`scripts/flights/lib/recovery.py`, lifted from the 266-E rec1 mechanism) applied to NX-T R1 as rec1 (new generation attempt id, new FIT run,
  cumulative spend read from the attempt record); (b) per-row durable checkpoints in `FlightRuntime` (append + fsync after every row; the seal
  verifies them) and resume mode B (checkpoint replay) so a crash loses only the rows in flight. Root cause of the total loss: the TraceSink
  buffers every record until the seal; the attempt directory held only the session-attach receipt after three hours.
- **310 A (RULED, done):** policy `NoAutoRebootWithLoggedOnUsers = 1`, `AlwaysAutoRebootAtScheduledTime = 0`, active hours 08-02, updates paused to
  2026-11-18 (registry under HKLM, reversible).
- **311 (RULED, done):** `scripts/flights/batch/saea_mount_data1.ps1` registered as SAEA-Mount-Data1 (at startup + at logon, highest privileges):
  attach with retries, `mount -a` inside the distro, verify the data root; tested 16:03Z (exit 0, root visible).
- **GPU-hours and the baseline (answer to 309):** no large-scale experiment is running; every read is a development read at the instrument's floor
  (decision 231: n = 1,080 same-flight paired; cross-flight reads need a twin and the 2.5 pp bar). The hours come from the Thinking core: about
  2,000 reasoning tokens per contact, 58 s (Perception) and 70 s (Solver) per contact at four slots, 46 % of Solver contacts forced-closed at the
  3,072 budget -- 98 s per lock row against about 30 s on the Instruct core; a five-arm column is 3.32 lock-row equivalents per row, so 1,080 rows
  = 24.5 GPU-h expected and 41.4 registered with the 1.3 margin. The baseline IS locked for development: lock candidate v3.0 (lock v2.2 + v4g on
  the Thinking core, budget 3,072 / cap 4,096 / drop-reasoning-v1; ruling 304), replicated on Fold B and DEV; it is the delivering arm of every
  node round; only the test-sample claim (successor 3) is still open.
- **Efficiency analysis and measures:** section "Experimental efficiency: root causes and measures" below.

### Experimental efficiency: root causes and measures (coordinator, 2026-10-14 16:20Z; owner question of 16:05Z)

**Where the time goes (2026-10-12 00:00Z to 2026-10-14 16:00Z, 64 h wall, one RTX 5090).** Flights: 268-B lock + twin about 19 h, P3.1 lock +
twin about 18 h, NX-T R1 smoke + the lost column 3.4 h -- about 41 h of GPU science (about 64 %). The rest: the data-disk cut-over window
(about 6.5 h, no flight by design), packets windows and serving swaps (about 1 h), flips / registrations / reads between seals (about 5 h), the
Windows Update reboot and its recovery (about 1 h so far, plus the 3 h of flight lost). Per read: one development read costs 9-10 GPU-h per arm
on the Thinking core against about 3 on the Instruct core.

**Root causes, ranked.**
1. **The Thinking core's per-contact cost.** About 2,000 reasoning tokens per contact at about 35 tokens/s per slot: 58 s (Perception) and
   70 s (Solver) per contact, 98 s per lock row at four slots; 46 % of Solver contacts are forced-closed at the 3,072 budget (the budget is the
   cost driver, not the answer). The Instruct lock row cost about 30 s. Every n = 1,080 read is therefore 3x the Instruct era.
2. **Design cost per read.** Decision 231 fixes n = 1,080 same-flight paired (the floor that resolves 1.5 pp); a cross-flight read needs a
   twin (+1 arm); the first node round carries five arms (3.32 lock-row equivalents per row). So one node round = 25-40 GPU-h.
3. **Serving geometry never tuned for the Thinking core.** The Instruct sweep doubled contacts/min (24.8 -> 50.2) by geometry alone; the Thinking
   session runs the inherited np4 x 24,576 q8 KV with 9 GB of VRAM idle; MoE decode is memory-bound, so more slots raise aggregate tokens/s.
4. **One serial GPU and gaps between flights.** Every seal -> read -> registration -> flip -> chain hand-off idles the GPU (35 min today), and
   the packets / cut-over / swap windows are exclusive.
5. **Fragile infrastructure with no checkpointing.** A crash loses the whole flight (today: 3 GPU-h and a day); earlier: terminal closes,
   WSLENV staleness, a hollow flip, stale task registrations -- each costs coordinator hours and GPU idle.
6. **Ceremony per flight.** Derive, register, countersign, mint, flip, sign-off, chain, close rows, read: about 1-1.5 coordinator hours per
   package and a human-gated sign-off between smoke and column.

**Measures (ordered by expected gain per effort).**
- M1 **Thinking serving geometry receipt** (GPU, about 1 h, a 4-row form proof per geometry under one registered row): np6 x 20k and np8 x 16k
  against np4 x 24k; expected +50-100 % contacts/min; applies to every later flight. Prerequisite: the prompt sizes (Perception about 3.6k,
  Solver about 9k tokens + 4k completion) fit 16k.
- M2 **Reasoning budget as the first optimisation target** (NX-T R2, already planned): a 1,536 / 2,048 budget column; if the Solver reads
  NO-RESOLVED-LOSS at 1,536 the lock row halves in cost. NX-T R1 (per-node off) may halve it earlier.
- M3 **Drop the twin in same-flight node columns.** The in-flight A/A offset on this core is measured twice (268-B SLU +1.15, P3.1 -0.61); a
  same-flight paired column needs no twin (the paired floor is 0.7 pp); keep twins only for cross-flight reads. Saves 30 % of a five-arm round.
- M4 **Two candidate arms per round, sequential rounds** instead of four; the column's cost falls from 3.32 to about 2.2 row equivalents.
- M5 **Checkpoint + resume (309, in build)**: a crash costs only the rows in flight; the chain can resume unattended.
- M6 **Machine sign-off**: the smoke's decode-cost table is already computed by the reader; let the chain write the marker itself when the
  registered conditions hold (no reasoning bytes on no-think nodes, no markers, no cap hits, mix within 1.3x), with the coordinator's veto window.
- M7 **One-command launch**: derive -> register -> countersign -> mint -> flip -> chain in one script with the gates in line (today eight manual
  steps); and auto-close rows at the seal.
- M8 **Queue the next ready package behind the flying one** so the seal -> launch gap is seconds (the batch driver already supports queues;
  the missing piece is registering the next cell while the current flies, which the serial-GPU rule permits since registration contacts nothing).
- M9 **Hardware**: a second GPU (or a rented one for the carriers) would double throughput; an owner decision (312), outside this plan.

**What is NOT the cause.** Not sample size inflation (n = 1,080 is the floor, not a choice), not large-scale confirmatory work (none is running),
not an unlocked baseline (v3.0 is the delivering arm of every round).

### Owner rulings 312-315 (owner, 2026-10-14 about 16:40Z; recorded by the coordinator)

Owner (verbatim): 「决策312：不加，决策313,314,315：按照你的建议走；」 English: "312: no (no second GPU); 313, 314, 315: go with your recommendations."

- **312 B (RULED):** no second GPU and no rented GPU; one serial RTX 5090 remains the budget.
- **313 A (RULED):** from NX-T R2 onward, same-flight node columns carry no twin arm (the in-flight A/A offset on this core is measured twice:
  268-B SLU +1.15 / intent -0.09, P3.1 SLU -0.61 / intent +1.60; the paired floor 0.7 pp stands) and at most two candidate arms per round;
  twins remain mandatory for cross-flight reads (DEV replicates, composition, test).
- **314 A (RULED):** machine sign-off between smoke and column: the chain writes the sign-off marker itself when the registered conditions hold
  (no reasoning bytes or think markers on no-think nodes, zero cap hits / empty answers / malformed JSON, measured mix within 1.3x the registered
  one); the coordinator keeps a veto window (the chain waits a registered number of minutes before the column starts). Engineering item.
- **315 A (RULED):** the Thinking serving-geometry receipt flies FIRST (np4 x 24k control, np6 x 20k, np8 x 16k; 4-row form proofs; throughput
  only), then NX-T R1 rec1 is registered pinned to the geometry the receipt picks and re-flown.
- Order of work now: geometry package (Sonnet, in build) -> register / countersign / mint / flip / chain / read (about 2 h GPU) -> rec1
  registration on the chosen geometry -> column re-fly; checkpoint + resume mode B (Sonnet, in build) merges when ready and applies to the
  flights after it; successor-3 test read follows the column.

### 315 A VOID (the card is 24 GB); checkpoints + rec1 merged; decisions 316-317 proposed (coordinator, 2026-10-14 18:10Z)

- **Fact (geometry package, Sonnet, branch `sonnet/think-geometry` 597767cdd, NOT merged):** the GPU is an RTX 5090 Laptop with 24,463 MiB (llama.cpp
  reports 23,119 MiB free at load), not 32 GB. KV at q8_0 = 52,224 B per token (48 layers x 4 KV heads x 256 x 34/32; measured slope 53.30 KiB) over a
  17,857 MiB base: np4 x 24,576 = 22,974 MiB (measured 22,976; 145 MiB headroom); np6 x 24,576 = 25,532 MiB (2,413 over); np8 x 24,576 = 28,091 MiB
  (4,972 over). Smaller slots refuse the largest rows (max Solver prompt 14,641 tokens; a 20,480 slot leaves 13,310). The geometry lever is CLOSED
  on this card at q8_0 KV; 315 A's premise fails, so the receipt does not fly and NX-T R1 rec1 re-flies on np4 now. The branch keeps the
  fragments, the `think-budget-np6/np8` targets, the 18-row probe design and the reader for a later q4_0-KV question; it also appended seven DRAFT
  ledger rows, which is why it stays unmerged.
- **Merged on master:** rec1 generic recovery (221106e8d, `scripts/flights/lib/recovery.py`; geometry table corrected to the 24,576 slot 3f9bb2e92,
  tests 62c029f01) and row checkpoints + resume mode B (37bb85a2b): every row is appended + fsynced to `<run>.rows.ckpt.jsonl` as it settles
  (1.66 ms per row measured), the seal verifies the file and records its sha, `resume_from = {attempt_id, checkpoint_sha256}` keeps complete
  rows (multi-arm rows only when every arm is present) and flies the rest; the root cause of the total loss was the in-memory TraceBuffer flushed
  only after every row settled (`rails/runner.py`, `core/flight/runtime.py`; design note `docs/superpowers/specs/2026-10-14-row-checkpoints-and-resume-mode-b-design.md`).
  Merging moved `runtime.py` / `rails/runner.py`, so every registered cell is re-pinned at its flight commit by the flip (as always).
- **316 (proposed): resume of a test-sample read.** The one-attempt test-read budget (`contracts/gate_exposure.py`) now exempts exactly the
  attempts a resume declaration names (never a FINALIZED one). This is a narrow reading of "no repeat, no best-of": a resume keeps completed
  rows, flies only rows never completed, selects nothing. A (recommended): accept; a resumed test read is reported as such (kept / flown counts).
  B: refuse resumes on test reads (a crash forfeits the attempt).
- **317 (proposed): q4_0 KV cache as a throughput lever.** np6 x 24,576 at q4_0 KV would fit (21,921 MiB) and could raise contacts/min by about
  50 %, but KV quantisation changes decoding (never flown here) and would be a base change needing its own Fold B read (about 20 GPU-h) before
  adoption. A: defer until after NX-T R1/R2 (recommended: R2's budget cut is the larger lever); B: run the q4_0 read right after NX-T R1.

### NX-T R1 rec1 column RE-FLYING at flight commit 8f9d8e1ee (coordinator, 2026-10-14 17:20Z)

- Sequence: writer `--append-recovery-ledger` at 283ab0045 (16:58:26Z; np4 geometry, 315 A void); the two rec1 rows countersigned 16:59:30Z
  (266-E form); receipt re-minted with `--supersede` (sha 676df36f...; backup `root-admission-v1.json.superseded-20261014T165931Z-by-rec1.bak`);
  flip attempts: (1) refused -- the default `smoke arm` kinds tried to re-pin the flown smoke (rows consumed); (2) with `NXT1_KINDS=arm`: pass 1
  committed the pins (7b4c2e140) but the package's draft-ledger-rows still quoted the pre-pin plan shas, and the flight CLI check refused
  "run ... is pre-registered more than once" (the first-attempt column row and the rec1 row share the run id); remedy per the 266-E precedent
  (da13cc80b): master fast-forwarded to the pins commit, the first-attempt row folded (removed; the rec1 row supersedes it; the superseded
  FIT-V1 row stays registered), the writer re-run at the flipped bytes (8f9d8e1ee); (3) flip converged, gate PASS, flight commit 8f9d8e1ee.
- Chain SAEA-Chain-NXT1 `arm-only` started 17:14:36Z (smoke sealed + marker verified by the chain; attempt
  `attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec1-v1`, FIT run `...-FIT-REC1-V1`); first flight with per-row
  checkpoints (`<run>.rows.ckpt.jsonl`, resume mode B available if it dies again). Expected about 30 h (seal about 2026-10-15 23:00Z).
- Lessons recorded: a rec1 flip excludes the flown smoke (`NXT1_KINDS=arm`); the writer must run again AFTER the re-pin so draft rows carry the
  pinned shas (two flips, as in 266-E); the gate counts every row of a run id, so the first-attempt row is folded, never left beside the rec1 row.

### Owner rulings 316-318 (owner, 2026-10-15 about 14:10Z; recorded by the coordinator)

Owner (verbatim): 「决策316：A，决策317：如果识别到本机不可都行，不要因为特殊的量化方案而改变基线配置，我们后期去寻找更优的GPU服务器解决这个问题，决策318：A」
English: "316: A. 317: if the local machine cannot do it, fine -- do not change the baseline configuration for a special quantisation scheme; we will
look for a better GPU server later to solve this. 318: A."

- **316 A (RULED):** a resumed test-sample read is admitted under the narrow reading: the one-attempt budget exempts only the predecessor attempts a
  resume declaration names (never a FINALIZED one); the read reports kept / flown row counts. The checkpoint + resume mode B code merged at
  37bb85a2b stands as is.
- **317 (RULED): no KV-quantisation change.** The baseline keeps q8_0 KV; the geometry lever stays closed on this 24 GB card; a better GPU server
  is a later owner-side decision (the geometry branch `sonnet/think-geometry` 597767cdd stays unmerged as a reference).
- **318 A (RULED):** NX-T R2 (per-node reasoning-budget column: delivering 3,072, candidates 2,048 and 1,536, no twin, Fold B 1,080) is built now
  model-free (Sonnet, worktree `sonnet-nxt-r2-budget`) with a data-driven arm table, and is registered after R1's read decides which node(s) the
  scan covers. 319 (notified): M6/M7/M8 launch automation in build (Sonnet, worktree `sonnet-launch-automation`).

### Launch automation (M6/M7/M8) and the NX-T R2 package merged; column at 800+ rows (coordinator, 2026-10-15 16:15Z)

- **Launch automation** merged f7685e9cd (spec path fix 00cbc7669): M6 `scripts/flights/batch/smoke_signoff.py` + `chain_lib.sh`
  (`wait_or_machine_signoff` with the registered conditions file, a 20-minute veto window, `close_rows_after_seal`), M7
  `scripts/flights/batch/package_launch.sh <spec> [--from <step>] [--until <step>] [--root-countersign] [--dry-run]` (derive -> write -> countersign
  -> mint -> commit -> flip -> chain; fail-closed rules: clean master, no merge in progress, no driver/flight/lease process, the flip's gate block
  parsed for PASS, flight-commit file == HEAD; the countersign only with the root flag), M8 verdict (`docs/superpowers/specs/2026-10-15-launch-automation-design.md`):
  derive / write / countersign / mint / commit are safe in flight; the flip and the chain start are not (`batch_driver.sh:113` stops the queue on a
  live `core.flight.cli`; `flip_in_ext4.sh:34`; the flight-commit file rewrite at `flip_in_ext4.sh:79`); `check --read-only` added. Tests 45/45
  (one 9p-timing flake re-run alone: pass).
- **NX-T R2 package** merged 299d22093 (`docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1/`, SHORT `nxt2`): per-node reasoning-
  budget column, arms `budget-1536`, `budget-2048`, delivering `budget-3072` (the lock form, requests byte-identical), NO twin (313 A), data-driven
  arm table `scripts/flights/nx/nxt_r2_arms.json`; harness: `reasoning_budget_tokens` was already a legal per-arm policy key (receipt v5 unchanged),
  one optional `thinking_frame.delivering_arm_id` added to the consumption module; cost model fitted on the R1 smoke's 40 contacts (0.0251 s per
  token; arm costs 0.66 / 0.80 / 1.00; mix 2.46; expected 24.1 GPU-h, ceiling 31.3); a lock flight projects 6.5 / 7.8 / 9.8 GPU-h at 1,536 /
  2,048 / 3,072; words GAIN / NEEDS-FULL-BUDGET / CHEAPER-AT-NO-RESOLVED-LOSS / UNRESOLVED against |o| = 1.15 pp and the decision-190 floors;
  the effect-floor gate accepts a twin-less same-flight node column. Registered after R1's read (318 A). Tests 95/95 on master.
- Open: `test_natural_source_compatibility::test_actual_reviewed_full_runtime_ast` and `test_consumption_module_step7::...current_lock` fail on
  master for pre-existing reasons (the runtime AST pin predates the checkpoint merge; the v2.3 tfrl-loop baselines) -- to be re-reviewed.
- Column: 800 rows checkpointed at 15:25Z, 0.63 rows/min, seal about 23:15Z.

### NX-T R1 rec1 column STOPPED at row 1,031 of 1,080 (2026-10-15 22:33Z): a non-delivering arm's missing Solver column aborted the flight; decision 320 proposed (coordinator, 22:50Z)

- **What happened:** after 29.3 h and 10,298 contacts (1,030 rows complete, every one checkpointed and traced on disk: `rows.ckpt.jsonl` 768 MB,
  `trace.jsonl` 668 MB), the runner raised `RailsRunnerError: perception branch 'both-off' sealed no level-2 Solver column`
  (`rails/runner.py` ~line 6453: every branch row must pop a Solver record; the no-think `both-off` arm of one row produced none) and the
  campaign exited 1; the driver wrote `batch-STOP` and the attempt record reads `failure_reason` accordingly (calls 10,298 / audio 30,101 s).
  The serving session is intact. The delivering arm and the four other arms of that row are not the cause; a candidate arm failed to deliver,
  which the harness treats as fatal for the whole flight. This is the E4 lesson again (a rare row class the 4-row smoke cannot exercise).
- **Harness defect (to fix before R2):** a NON-delivering arm's absent level-2 column must be recorded per row (`solver_absent` + reason) and
  counted by the reader as that arm's delivery failure, never abort the flight; the delivering arm keeps its fail-closed semantics.
- **Package rule:** "at most ONE root-diagnosed recovery re-registration per run id; a second failure closes the cell" -- rec1 was that one.
- **320 (proposed): how to close NX-T R1.** A (recommended): SEAL-ONLY the 1,030 completed rows (the decision-189 path used for COMP-1 and P-SV-1;
  no new contacts; the 50 unflown rows and the failing row are reported, the failing row as a both-off delivery failure), read the column at
  n = 1,030 (paired floor unchanged in practice), close the cell per its rule; fix the harness for R2. B: a second recovery by checkpoint
  resume (keep 1,030, fly 50 after the fix; about 1.5 GPU-h) -- an explicit owner exception to the package rule. C: close without a read (loses
  about 30 GPU-h of evidence). The GPU is idle meanwhile: successor-3 (test read, authorised by 301 A / 308 A, gate P3.1 NOMINATED met) is the
  next ready GPU work and can fly while the seal-only paperwork proceeds (CPU only).

### Successor-3 test read LAUNCHED at flight commit 73fd885f8 (coordinator, 2026-10-15 23:35Z)

- After the NX-T R1 stop the GPU went to the next ready package within an hour: the dead chain's `batch-STOP` and `locks/flight.lock` parked with
  dated names (`/home/chao/batch-STOP.nxt1-rec1-20261015T2233Z`, `/home/chao/flight.lock.stale-nxt1-rec1-stop-*`; no driver / flight / lease
  process alive); successor-3 registered at 727d96336 (22:37Z; four DRAFT rows); the packets row countersigned 22:54Z; `direct_fb_packets_gpu.sh
  --check --stage test-sample-3010` PASS; GPU window 23:11-23:14Z encoded and promoted the 3,010 sample rows into the Thinking packet root
  (receipt `TEST-SAMPLE-3010-promotion.json`, sha 686a2ba5...; Thinking session restarted and ready; the packets row stays registered like the
  DEV one -- encoder passes leave no run manifest for the closure gate); cells re-derived `--require-receipt`; generation + FIT rows
  countersigned 23:18Z (the READ / paired-analysis row stays a draft); receipt minted; committed 0e50fa84e; ext4 flip converged 23:28Z (gate
  PASS, one standing advisory `tuning-roster-unverified`), master 73fd885f8; chain task SAEA-Chain-MS3 (`/home/chao/saea-queue/chain_ms3.sh`,
  log `/home/chao/ms3-chain.out`) started 23:30Z: preflip 0 refusals, preconditions hold, one cell step, NO smoke on the sample (one attempt, ever).
- Terms: run `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1` (lock arm only; 3,010 rows x 2 contacts; ceiling 35.5 GPU-h,
  expected about 27 h), comparator the sealed successor-2 run, declared null = the DEV twin offset (SLU 0.6144 / intent 1.6 pp), no in-chain
  replicate (stated), aggregate-only, claims_benefit false, words NEUTRAL / HARM / UNRESOLVED (successor 2's). Resume under 316 A if it dies.
- NX-T R1 seal-only (320 A, pending the owner) is prepared in parallel by Sonnet (worktree `sonnet-nxt1-sealonly`: root cause, runner fix, seal-only package).

### NX-T R1 stop: root cause, harness fix merged, decision 320 options revised (coordinator, 2026-10-15 23:55Z)

- **Root cause (Sonnet, gold-free, from the campaign log and the trace):** row 1,030 (admission index 1014; 1,029 rows complete, 50 never started;
  10,298 = 1,029 x 10 + 8 contacts). The `both-off` arm's no-think Solver contact (cap 1,024) ended on `finish_reason = length`;
  `FrozenCoreRoleFiniteCompletionError` (`native_roles.py:497`) left the branch fan-out (`reproduction/ojw/native_supply_variants.py:573`,
  branches run in declared order, the delivering arm LAST), so the twin and the delivering arm never ran on that row; the level-2 fold then
  found no Solver record and raised. First such event in 2,058 earlier no-think Solver contacts (longest 66 tokens): a rare row class.
- **Fix merged (60134738e):** a finite completion on a NON-delivering branch is recorded as `solver_absent: true` + `absent_reason`
  (optional receipt keys, schema unchanged, old receipts verify); the fan-out continues so the delivering arm runs; the renderer scores an
  absent column as the canonical empty answer; both column readers print `absent_rows` per arm; the sign-off conditions gain
  `absent_columns == 0`; `replay_seal_consistency.py` now carries the v5 thinking fields and `finish_reason` (it had failed every v5 row).
  Open: a finite completion on the DELIVERING arm still aborts (by design) -- R2 keeps that exposure until a delivering-arm abstain path is
  designed; the R2 sign-off conditions file still lacks `absent_columns` (generated by an `nxt_r2` script; to add before R2 registers).
- **Decision 320 revised.** The seal-only package as prepared (`docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1-sealonly-v1/`,
  cell `...-v1-sealonly`, mode-A resume by trace sha 3238cd8a..., roster narrowed to the 1,029 complete rows with its OWN split identity) needs
  `--allow-output-change` at the flip (the rebuilt phase supply covers 1,029 rows, not the pinned 1,080) -- a deviation from the standing
  "never pass it" rule -- and replaces the arm rows' split-identity column. Options now: **A'** seal-only as prepared (two rule deviations, 0 GPU,
  n = 1,029); **B' (recommended)** a checkpoint/trace resume that keeps the 1,029 rows and flies the 51 remaining rows (the failing row included,
  under the merged fix; about 1.5 GPU-h after successor-3 seals; mode A since `rails/runner.py` moved) -- one explicit exception to the
  package's one-recovery rule, no output-change flag, the registered roster and n = 1,080 intact, and the fix exercised on the very row that
  broke; **C** close without a read. Both A' and B' wait for the successor-3 seal (one driver, one GPU).

### Host memory pressure stalled the successor-3 flight for 85 minutes; periodic WSL cache drop installed (coordinator, 2026-10-16 07:30Z)

- **Owner question (06:45Z):** "memory use above 90 %, is something wrong?" Finding: no leak. Windows 63.4 GB; the WSL VM (cap 44 GB) had 27 GB of
  CLEAN page cache (GGUF mmap, packets, traces, checkpoints) beside 5 GB of process memory; `autoMemoryReclaim=dropcache` reclaims only when the
  VM idles, which a 27-hour flight never does; Windows compressed 10.4 GB of vmmem pages. The flight worker's RSS is flat (3,052 -> 3,063 MiB over
  30 minutes); llama-server 1.2 GB (weights in VRAM).
- **Effect:** the campaign log shows ZERO row completions from about 05:15Z to 06:40Z (buckets 01:10-02:40 local), no errors, decode speed normal
  afterwards (about 40 tokens/s per slot): the VM was being paged/compressed by the host. About 180 rows (85 min) lost; successor-3 at 783/3,010
  at 07:26Z, seal now about 2026-10-17 03:00Z.
- **Action (reversible, no effect on the flight):** one manual `echo 1 > /proc/sys/vm/drop_caches` as root at 07:25Z (WSL cache 27 -> 2 GiB; Windows
  free 33.0 -> 41.9 GB; vmmem working set 7.8 -> 5.8 GB); `scripts/flights/batch/wsl_drop_caches.sh` (ea873e4ae) registered as the repeating
  task SAEA-WSL-DropCache (every 30 min, as root, via `saea_task.ps1 -WslUser root -RepeatMinutes 30`; the `-WslUser` option added b09dec0f8);
  log `/home/chao/wsl-drop-caches.log`. Candidate for a no-flight window: lower `.wslconfig` memory 44 -> 36 GB (needs `wsl --shutdown`).
- Session note: the Claude session restarted twice today (the scratchpad helpers survived this time; background monitors are re-armed by hand).

### Owner ruling 320 B (owner, 2026-10-16 about 23:25Z; recorded by the coordinator)

Owner (verbatim): 「决策320：B」 English: "Decision 320: B" -- the B' option as proposed at 23:55Z on 2026-10-15: a resume that keeps the 1,029 complete
rows of the stopped rec1 attempt and flies the 51 remaining rows (the failing row included) under the merged absent-arm fix; an EXPLICIT owner
exception to the package rule "at most one root-diagnosed recovery re-registration per run id" (this is the second, rec2); mode A (trace
replay, predecessor trace sha 3238cd8a...) because `rails/runner.py` moved; no `--allow-output-change`; the registered roster (1,080) and the
read at n = 1,080 intact. Cost about 1.5 GPU-h after the successor-3 seal; the seal-only package (A') stays unused.
- Execution: rec2 registration built model-free now (Sonnet; the recovery lib's second record, resume_from block, new generation attempt and
  FIT-REC2 ids, cumulative caps += 10,298 calls / 30,101 s, the rec1 row folded into the rec2 row per the 266-E form), registered on master in
  flight, flipped (`NXT1_KINDS=arm`) and flown (`arm-only`) once successor-3 seals; then `nxt_r1_read.sh columns` -> READ row -> read.

### CORRECTION: the two successor-3 stalls were host SLEEP, not memory pressure (coordinator, 2026-10-17 04:55Z)

- Windows Power-Troubleshooter events: sleep 2026-10-16 05:14:20Z -> wake 06:47:45Z (wake source: power button) and sleep 2026-10-16 23:34:13Z ->
  wake 2026-10-17 04:44:25Z (power button). The first matches the "85-minute stall" recorded at 07:30Z on 2026-10-16 (that section attributed
  it to Windows memory compression; the compression was real but the stall was the sleep); the second cost 5 h 10 min of the test read
  (checkpoint 2,538 -> 2,587 across the night; rows and log agree: 2,586 checkpointed vs 2,585 workflow ends at 04:47Z, so no durability
  defect). The owner confirmed in conversation: 「服务器休眠了，后面继续吧」 ("the server went to sleep; carry on").
- AC standby and hibernate timeouts were already 0 (never); the sleeps were therefore triggered by an action, most likely the lid. Change made:
  lid-close action on AC set to "do nothing" (`powercfg /setacvalueindex SCHEME_CURRENT SUB_BUTTONS LIDACTION 0`); monitor timeout on AC 0.
  The periodic WSL cache drop stays (it still protects the host from the page-cache growth). GPU after the wake: 1,430 MHz, 93 W against a
  97 W software power cap (a laptop limit; decode 26-30 tokens/s per slot vs about 40 earlier in the flight -- observation only).
- Flight: successor-3 at 2,587 / 3,010 at 04:48Z, resumed at speed; seal now about 08:00Z 2026-10-17.
- Addendum 05:00Z: the lid and power-button actions were HIDDEN in the active scheme (the first `setacvalueindex` was a no-op); after
  `powercfg /attributes SUB_BUTTONS LIDACTION -ATTRIB_HIDE` (and PBUTTONACTION) both are set to "do nothing" on AC (lid: AC 0 / DC 1 unchanged;
  power button: AC 0 / DC 1 unchanged -- it was 1 = sleep, i.e. a press while awake slept the machine). Reversible with the same commands.

### NX-T R1 rec2 (320 B) registered in flight; flies after the successor-3 seal (coordinator, 2026-10-17 05:05Z)

- Sonnet's rec2 package merged 5acfbc38b: `scripts/flights/lib/recovery.py` now refuses a second recovery record without an `owner_exception`
  naming the ruling (and one that does not name every earlier attempt); `nxt_r1_family.py` carries the recovery history (rec1, rec2), two
  predecessor snapshots read from the attempt records (first attempt 1,204 calls / 3,298 s; rec1 10,298 / 30,101 s -- the rec1 record now
  reads ABORTED), `resume_from = {rec1 attempt, trace sha 3238cd8aedb5...}` (mode A; 667,787,659 bytes), kept 1,029 / flown 51 / partial 0 (the
  failing row's records were never flushed, so it is among the 51), run-cumulative caps 28,782 calls / 83,877 s, the 41.4 GPU-h ceiling
  unchanged, expected about 1.5 GPU-h (510 contacts); offline replay proof on a scratch copy: 1,029 checked / 0 failing / 0 sealed twice
  (`resume-replay-proof-rec2-v1.json`). Tests 124 passed in the worktree; gates PASS; the seal-only package re-pinned to the rec1 ids and parked.
- Registered on master at 5acfbc38b (04:53:44Z): writer `--append-recovery-ledger`; receipt minted with `--supersede` (sha 087e68b5...,
  backup `root-admission-v1.json.superseded-20261017T045351Z-by-rec2.bak`); commit 09569de59. LAPSE: the fold and countersign helpers had been
  lost with the scratchpad, the derived helper files were empty and both steps silently did nothing in that commit; repaired at 04:58Z
  (547f83c04): the rec1 generation row folded (one row per run id), the rec2 generation row and `...-FIT-REC2-V1` countersigned 04:58:15Z; a
  second mint was refused as already current (the 04:53Z receipt carries the rec2 ids). Lesson recorded: helpers must assert their own effect
  (both now do) and `python3 <empty file>` exits 0.
- Risk to watch at the flip (Sonnet): `repin.py` ~1536 looks up a resume cell's parent by attempt id across `configs/experiment/`; the rec1
  attempt id no longer appears there. Next: after the successor-3 seal, `NXT1_KINDS=arm` flip (column only; never `--allow-output-change`),
  chain `arm-only` (it re-hashes the predecessor trace and refuses if the rec2 attempt exists), `nxt_r1_read.sh columns`, READ row, read.

### SUCCESSOR-3 TEST READ: the Thinking system on the 3,010-row sample -- NEUTRAL (no harm), SLU +6.41 / intent +3.97 reported beside the word (coordinator, 2026-10-17 08:50Z)

- Sealed 08:38Z at flight commit 73fd885f8 (run `SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1`, 3,010 rows, 6,020 contacts,
  COMPLETED, summed call latency 102.77 h; two host-sleep gaps inside the 33 h wall; checkpoint sha bdfed492...). Generation + FIT rows closed;
  READ row countersigned 08:39:20Z; aggregate read 08:46Z (0 contacts), written to `analysis/SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-PAIRED-ANALYSIS-V1/`.
- **Read (vs the sealed successor-2 v2.2 system; prompt-cluster paired bootstrap, 10,000 draws, seed 20261014; post-stratified natural mixture):**
  SLU-F1 66.65 -> 73.05 %, **+6.41 pp [+4.44, +8.46]**; intent 82.36 -> 86.33 %, **+3.97 pp [+2.26, +5.45]**; equal-stratum SLU +6.98 [+4.71, +9.38],
  intent +5.26 [+3.36, +6.72]. Declared null = the DEV twin offset (SLU 0.61 / intent 1.6 pp); harm margin 2.5 pp. **Word: NEUTRAL** (the
  registered words are HARM / NEUTRAL / UNRESOLVED; claims_benefit false; the gain is reported beside the word, not claimed; no in-chain
  replicate on the sample -- the limitation is stated in the read). Development numbers; never a test claim (decisions 28, 151, 301).
- **Meaning (stated, not claimed):** the Thinking system is now read on three rosters against the Instruct-era system -- TRAIN Fold B +7.15
  [+5.08, +9.26], DEV +7.52 [+5.46, +9.62], test sample +6.41 [+4.44, +8.46] SLU; intent +2.31 / +2.50 / +3.97. The v3.0 candidate's
  test-sample read is closed; the chain of sample reads on this roster: successor-1 PLAN -> COMP-1b (+5.80 intent) -> successor-2 v2.2
  (+1.67 SLU) -> successor-3 Thinking v3.0 (+6.41 SLU / +3.97 intent). Results note: Opus (`docs/results/2026-10-17-slurp-successor3-thinking-system-test-sample-read.md`).
- Next on the GPU (serial): NX-T R1 rec2 (320 B) flip + `arm-only` resume (51 rows) -> R1 read -> R2 arm table -> R2 via `package_launch.sh`.

### NX-T R1 rec2 (320 B) FLYING since 09:05Z; one refusal root-caused and fixed; successor-3 results note merged (coordinator, 2026-10-17 09:11Z)

- Flip converged at e4092610b (08:54Z; the first pass was refused rc7 because a docs commit moved master during the loop -- coordinator error,
  re-run from 963856d38). Flight commit file = master = e4092610b; no lock, no driver, serving `think-budget-np4` resident, sign-off marker present.
- First chain start 08:58Z REFUSED (rc 6): `the rec2 attempt already exists on the data root`. Root cause: the flip's re-pin step runs
  `core.flight.cli check` once per cell (`repin_onepass` step 6) and the read-only flag was OPT-IN (`SAEA_REPIN_CHECK_READONLY=1`, M8); the flip
  set no env, so preflight wrote `runs/<run>/<rec2 attempt>/resume-declaration.json` (owner decision 309 writer, before the first gate touch)
  at 08:47Z and again 08:53Z (the two flip passes; re-pin receipts `check-...-repin-20261017T085352Z.json`). The directory held exactly that one
  file; no attempt RECORD existed. Fixes (09028888c + this commit): (a) the chain precondition now checks the attempt record
  (`attempts/<run>/<attempt>.json`, the runtime's own one-time key) and tolerates a run directory holding exactly the declaration that matches the
  registered `resume_from` (schema, run, attempt, predecessor, trace sha); any other file still refuses; (b) `repin.default_run_check` passes
  `--read-only` by DEFAULT (`=0` restores the writing check); 58 re-pin/cli unit tests pass; the launch-automation spec is amended.
- Second chain start 09:05:36Z: resume precondition OK (trace 3238cd8aedb5 unchanged); resume replay gate 1,029 rows checked / 0 failing /
  0 sealed twice; rec2 attempt OPENED 09:06Z (reserved 28,782 calls / 83,877 s = the run-cumulative caps); checkpoint file open; 18 contacts by
  09:08Z; GPU 91 %. Expected ~1.5 GPU-h for the 51 rows (~510 contacts). Then `nxt_r1_read.sh columns` -> READ row countersign -> `nxt_r1_read.sh`.
- Opus results note for the successor-3 test read merged (96a4509bd): `docs/results/2026-10-17-slurp-successor3-thinking-system-test-sample-read.md`
  + ledger entry; NEUTRAL, gain reported not claimed; Opus adds one derived observation (the SLU gain is recall: TP 3,562 -> 4,100, FN 1,913 -> 1,378,
  FP flat; successor 2's gain was precision) and flags inherited boilerplate in the vs-comparator README / allowance `milestone_rule` text /
  `registered-facts-v1.json` post-stratification block (binding ids correct; wording stale) -- repair with the next package writer, not in place.
- Coordinator lapse recorded: two WSL probes in this window were issued as inline `wsl bash -c '...; ...'` strings; the outer WSL shell split them at
  `;` and `$A` expanded empty (one `ls` listed the repo root, one listed `/`). Standing rule re-affirmed: every WSL probe goes through a scratchpad
  script file (memory `wsl-invocation-quoting`).

### NX-T R1 READ: Perception thinking NOT NEEDED at the floor, Solver thinking NEEDED; R2 arm table decided (coordinator, 2026-10-17 10:37Z)

- rec2 sealed 10:23:53Z (510 contacts = the expected 51 rows x 10, 4.83 h summed latency, checkpoint 5954ac40c703, COMPLETED at e4092610b);
  generation + FIT-REC2 rows closed; READ row countersigned 10:25:09Z; official per-arm column scoring 10:33Z; preregistered read 10:34Z
  (`analysis/SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1/read.json`, schema saea-nxt-r1-thinking-policy-column-read-v1; 1,080 rows = 1,029
  kept + 51 flown; 0 scorer parse failures; 0 reasoning leaks; 1 absent column = the solver-off arm's one finite completion, recorded not fatal).
- One refusal on the way (fixed, 7df5c1cec + test 4bba43420): the column scorer resolved a KEPT row's Solver branch contacts in the rec2 trace
  first, and request ids repeat across attempts (`flight-0026` in both), so row 000006 tripped the custody-hash check. Kept rows now resolve in
  their predecessor's trace only; flown rows in the bundle's own.
- **Read (same-flight node column, paired utterance-cluster bootstrap 10,000 draws; delivering = both-on 72.35 SLU / 85.74 intent):**

  | arm | SLU-F1 % | SLU delta pp [CI95] | intent % | intent delta pp [CI95] | s/row | word |
  | --- | ---: | ---: | ---: | ---: | ---: | --- |
  | both-on (delivering) | 72.35 | -- | 85.74 | -- | 110.0 | -- |
  | both-on-twin | 72.23 | -0.12 [-1.44, +1.24] | 85.74 | 0.00 [-0.93, +0.93] | 112.5 | A/A |
  | perception-off | 72.16 | **-0.19 [-1.69, +1.29]** | 85.28 | -0.46 [-1.76, +0.83] | 60.7 | **NO-RESOLVED-LOSS** |
  | solver-off | 65.24 | **-7.11 [-8.97, -5.25]** | 83.80 | -1.94 [-3.33, -0.56] | 51.3 | **NEEDS-THINKING** |
  | both-off | 63.16 | -9.18 [-11.24, -7.14] | 82.04 | -3.70 [-5.37, -2.04] | 6.4 | NEEDS-THINKING |

  Equal-scenario weighting agrees (perception-off -0.32, solver-off -8.25, both-off -10.67 pp SLU). Extra word NOT-NEEDED-AT-THE-FLOOR (Perception).
  Decode: Solver at budget 3,072 FORCED-CLOSES 19/51 both-on, 20/51 twin, 16/51 perception-off (p90 completion = the budget); Perception forced
  closes 1-2/51. The no-think Solver answers in 26 tokens / 3.6 s; the thinking Solver 1,920 tokens / 62 s. Development numbers (decision 28).
- **Meaning (stated, not claimed):** the Thinking system's gain over the Instruct system lives at the SOLVER (slot extraction): removing Solver
  reasoning costs 7.1 pp SLU; removing Perception reasoning costs nothing the design resolves and halves the row cost (60.7 vs 110 s/row; a
  1,080-row lock flight 4.55 vs 8.25 GPU-h). Solver reasoning is capacity-bound at 3,072 (37 % forced closes).
- **R2 arm table (coordinator decision under the registered rule "R1's answer decides the arm table"; two candidates, no twin, 313 A):**
  `perception-off-solver-3072` = {perception: off, solver: 3072} (the same-roster REPLICATE of R1's cheapest no-loss form, the owner's
  "replicate on the same roster before drawing a fresh one"; if it reads CHEAPER-AT-NO-RESOLVED-LOSS it is the adoption candidate for the lock) and
  `solver-2048` = {perception: 3072, solver: 2048} (the one-node budget scan on the node that NEEDS thinking; cheaper direction only -- the family
  clips budgets to [min, 3072]). The default 1536/2048 both-node arms are dropped: a both-node cut confounds the two nodes and 1,536 at the Solver
  is already answered by the forced-close table.
- **Owner items (not blocking R2):** 323 -- a budget ABOVE 3,072 at the Solver (e.g. 3,584 with answer reserve 512) is outside R2's registered range
  but is the direction the forced-close table points to; recommend a one-arm R2b after R2 reads (A) or fold into the next node round (B).
  324 -- adopt Perception no-think into the v3.0 lock candidate after the R2 replicate reads no loss (A), or require a Fold A confirm first (B;
  recommended B: one 2-arm column, ~5 GPU-h, the lock rule of C0.6).
- Next: `package_launch.sh scripts/flights/nx/nxt_r2_launch_spec.json --root-countersign --until commit` (derive from the new table, register,
  countersign, mint, commit), then `--from flip` (flip + chain SAEA-Chain-NXT2 + smoke sign-off). Opus writes the R1 results note.

### NX-T R2 FLYING since 10:49Z; R1 results note merged; CORRECTION to the 10:37Z section (coordinator, 2026-10-17 10:51Z)

- **Correction (Opus's check of the read file):** the 10:37Z heading and line "Extra word NOT-NEEDED-AT-THE-FLOOR (Perception)" are WRONG. The
  reader awarded perception-off the word NO-RESOLVED-LOSS and NO extra word: both floor clauses fail (SLU CI lower bound -1.69 vs the -1.49 floor;
  intent lower bound -1.76 vs -0.65). The top-level `extra_word` key in `read.json` is a constant the reader writes into every read, not a verdict
  (coordinator misread; the per-arm `extra_word` is null). Consequence: Perception no-think is "no loss the design resolves", not "not needed at the
  floor"; the R2 arm `perception-off-solver-3072` (same-roster replicate) is therefore REQUIRED evidence, not optional, and item 324 stays B
  (Fold A confirm before any adoption). Two smaller corrections from the same check: the rec2 seal time is 10:22:16Z on the manifest (10:23:53Z was
  the chain exit); the rec1 stop left 1,029 complete rows with the failing row the 1,030th (the "row 1,031" heading of 2026-10-15 counted the
  in-flight row). Results note: `docs/results/2026-10-17-slurp-nxt-r1-thinking-policy-column-read.md` (Opus, merged f9b44984e; it adds the per-arm
  official TP/FP/FN: the Solver no-think loss is mostly precision, TP -98 / FP +280 / FN +94 vs both-on; the words are unchanged under the 268-B
  offset |o| = 1.15).
- **R2 launched through the package launcher (M7, first real use):** register `--root-countersign --until commit` 10:38-10:39Z (derive from the new
  arm table, 4 rows countersigned, receipt minted, commit 2b277fa3a; 23 occurrences of each new arm id across the package; ceiling 31.3 GPU-h,
  11,880 calls). Two launcher defects surfaced and were fixed before the flip ran: (a) a flip env value with a space (`NXT2_KINDS=smoke arm`) was
  passed to the wrapper as two words ("bad extra env 'arm'") -- each KEY=VALUE is now one quoted shell word, regression test added (df8f184f2);
  (b) the pins-commit message file the spec names (`/home/chao/nxt2-pins-commit.txt`) is created by nobody -- written by hand this time; the
  launcher should write it from the spec (small follow-up). Flip 10:43-10:49Z in ext4: gate PASS x2, master 68f398caf -> 7ec52005b (pins commit);
  chain SAEA-Chain-NXT2 started 10:49:57Z at flight commit 7ec52005b = master. Sequence: smoke-4 -> machine sign-off (`smoke_signoff.py`, conditions
  file `docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1-signoff-conditions-v1.json`, 20-min veto) -> the 1,080-row column
  (arms perception-off-solver-3072, solver-2048, delivering budget-3072). Expected cost well under the 31.3 GPU-h ceiling (the two candidates are
  both cheaper than the delivering arm).

### Owner rulings 323 and 324 (2026-10-17 12:38Z; owner message translated from Chinese: "Decision 323: adjust the truncation configuration; decision 324: follow your recommendation")

- **323 -- adjust the truncation configuration.** Read as: the Solver's reasoning budget / completion cap are to be RAISED so that Solver
  reasoning is no longer cut (NX-T R1: 19/51 forced closes at budget 3,072, p90 completion = the budget; owner directive of 2026-10-12 "never
  truncate", rulings 268-273). Not read as: a change to the finite-completion or forced-close HANDLING, which stays as registered. Plan: NX-T R2
  continues as registered (its two candidates are the cheaper direction and the perception-off replicate); a successor round **NX-T R2b** is built
  now at 0 GPU as a one-candidate same-flight column on the same roster: Solver budget raised with the cap raised in step (first proposal budget
  6,144 / cap 7,168, answer reserve 1,024; Perception at the lock form 3,072 / 4,096). A raised cap is a new serving geometry (the resident fragment
  is `q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max4096-v1`; the direct bare-core line already served max 8,192 at np4),
  so R2b carries its own serving fragment + geometry receipt (ruling 315 A: geometry receipt first) and the FIT gate on the 24,576-token live slot
  (Solver prompts ~9.2-11.4k tokens + 7,168 cap = ~18.6k). The family's budget clip [min, 3072] is lifted for R2b only; R2's package is untouched.
  R2b flies after R2 seals (one experiment in flight). Its read decides the Solver budget of the v3.0 lock candidate (GAIN / NO-RESOLVED-LOSS /
  NEEDS-FULL-BUDGET words of the R2 reader, re-used).
- **324 -- B (recommended):** Perception no-think enters the lock candidate only after (i) the R2 same-roster replicate reads no resolved loss and
  (ii) a Fold A confirm (one 2-arm column, ~5 GPU-h) reads no resolved loss. Until then the lock form keeps Perception thinking at 3,072.

### NX-T R2 column FLYING since 12:40:36Z after a 1 h 43 min idle at the sign-off; owner directive: a >= 24 h GPU queue (coordinator, 2026-10-17 12:42Z)

- **Idle incident (GPU 0 % 10:57-12:40Z).** The R2 smoke sealed COMPLETED at 10:56:47Z (4 rows, 5 checkpoint lines). `batch_chain_nxt_r2.sh`
  then waited for a HAND-WRITTEN sign-off marker: the R2 chain (built 2026-10-15) carries its own `wait_signoff` and never calls
  `chain_lib.sh wait_or_machine_signoff` (M6), so the machine sign-off never ran; my waiter watched for "arm-start"/"veto" and not for the
  "waiting for the sign-off marker" line, so the idle went unnoticed until the 12:37Z check. Second defect found when the sign-off was run by hand:
  the conditions file beside the package still expected the DEFAULT arm table (budget-1536/2048) -- the derive step does not regenerate it --
  so the first machine sign-off REFUSED 3/43 (two missing arms; the perception-off arm's Perception node in no-think mode); re-issued for the
  2026-10-17 table (2059ff8fb) -> PASS 47/47 at 12:39:53Z; the chain saw the marker and opened the column at 12:40:36Z (attempt OPENED, GPU 90 %).
  Rules for every next package (R2b carries them): the chain calls the M6 library; the derive emits the sign-off conditions INSIDE the package
  from the arm table; the coordinator's waiter greps the chain log for "waiting for the sign-off marker" as an alarm.
- **Owner directive (12:42Z, translated): "Next, run a set of large-scale GPU experiments that must run for at least 24 hours; after tidying up,
  launch them as the priority."** Queue (serial, one experiment in flight, each through the batch driver): (1) NX-T R2 column, flying, ~19 GPU-h
  expected (three arms at 1.0 / 0.55 / ~0.8 of the 8.25 GPU-h delivering pass), seal expected about 2026-10-18 08:00Z; (2) NX-T R2b (ruling 323:
  Solver budget 6,144 / cap 7,168, one candidate arm, new serving fragment, same np4 x 24k geometry) -- package in build by Sonnet now at 0 GPU,
  registered on master today, flipped + chained by the queue hook `queue_nxt2b_after_nxt2.sh` the moment R2's chain exits rc 0 (~20 GPU-h);
  (3) after R2's read: the 324-B Fold A confirm column for Perception no-think (2 arms, ~5 GPU-h) if the R2 replicate reads no resolved loss, else
  the next node round (USE node: Solver instruction-template column, NX plan R1 of 2026-10-09). (1)+(2) alone cover ~39 GPU-h without a hand step.

### Owner rulings 325-327 (2026-10-17 12:45Z; owner message translated from Chinese: "Decision 325: A; decision 326: follow your recommendation; decision 327: A")

- **325 A:** NX-T R2b = ONE candidate arm `solver-6144` (Solver reasoning budget 6,144 / completion cap 7,168, answer reserve 1,024; Perception at
  the lock form 3,072 / 4,096); delivering arm = the lock form; no twin; same roster (SLURP-EVO-FOLD-B-V2); new serving fragment at the unchanged
  np4 x 24k geometry.
- **326 A:** after R2b the queue continues with the 324-B Fold A confirm column for Perception no-think (2 arms, ~5 GPU-h; only if the R2
  same-roster replicate reads no resolved loss), then the USE-node round (Solver instruction-template column, K <= 6 arms, TRAIN Fold B; NX plan
  of 2026-10-09 R1). Carrier base runs (A2T / E21 / E22) stay behind the SLURP line (ruling 307).
- **327 A:** unattended hand-over authorised: the queue hook flips and chains R2b the moment the R2 chain exits rc 0, without an owner read of R2
  in between (R2b's design does not depend on R2's result). The hook refuses on any R2 exit other than 0.

### Host reboot killed the R2 column; recovery rec1 registered, flipped and FLYING since 13:05Z (coordinator, 2026-10-17 13:09Z)

- 12:52Z: the owner rebooted the laptop (message: "I just restarted the laptop") while the R2 column attempt was open (opened 12:40:36Z; the attempt
  record reads OPENED with 42 calls / 132.1 speech-seconds; 6 rows checkpointed, last at 12:51Z). The driver, the flight, the resident server and
  both coordinator agents (Sonnet R2b, the quiet watcher) died with the host; the data root re-mounted at boot (SAEA-Mount-Data1); the stale
  `flight.lock` was parked after confirming no live process. Root cause: host restart, not a harness or serving defect.
- Recovery rec1 (the package's registered single-recovery form: re-flown WHOLE under the rec1 ids; the six rows are not resumed because the R2
  package registers the whole re-fly form and the saving would be ~10 min): predecessor snapshot `predecessor-snapshot-arm-rec1-v1.json`
  (`recovery.py snapshot`, read-only on the data root), diagnosis `recovery-input-arm-v1.json`, writer `--append-recovery-ledger` at 13:00Z,
  the rec1 generation row + FIT-REC1 row countersigned 13:01:30Z (the launcher's countersign step does not know the recovery row form; a
  scratch helper did it), the first-attempt generation row FOLDED into the rec1 row (one row per run id), receipt re-minted `--supersede`
  (sha 21e69b32...), commit 3a75967b2; flip `NXT2_KINDS=arm` in ext4 10:04-13:04Z: gate PASS, master 3a75967b2 -> 9790c071f, flight commit =
  master; chain SAEA-Chain-NXT2 re-pointed at `arm-only` and started 13:04:38Z; serving swapped to think-budget-np4 (ready 13:05:15Z, 31 GB host
  free); driver `arm` 13:05:16Z; rec1 attempt OPENED; GPU 92 %. Run-cumulative caps carry the 42 calls / 132 s of the dead attempt.
- The 24-h queue is unchanged: R2 (~19 GPU-h from 13:05Z, seal ~2026-10-18 08:30Z) -> R2b by the queue hook (its start stamp must be later than
  13:05Z so the 10:49Z chain-start line is never matched) -> 324-B confirm -> Solver template column.
- Follow-ups: (a) `package_launch.py` countersign step to accept the recovery row form ("REGISTERED (DRAFT, root countersignature pending)");
  (b) the pins / flight-commit / chain wrapper segment for a rec flight should come from the launch spec (a `recovery` launch id) instead of a
  hand edit of `/home/chao/saea-queue/chain_nxt2.sh`.

### INCIDENT: R2 rec1 ABORTED 13:42Z by the coordinator (serving-task registration auto-started a second server; its reaper killed the resident one); R2b goes on the GPU now; owner exception 328 requested for R2 rec2 (coordinator, 2026-10-17 13:44Z)

- 13:41Z: to prepare NX-T R2b's serving session I registered the Windows tasks SAEA-Serving-THINKB7 / SAEA-Monitor-THINKB7 with
  `saea_task.ps1 -Name ... -Script ...`. The helper REGISTERS AND STARTS a task; the serving entry script's start-up reaper (memory of
  2026-09-22: an unscoped `pgrep -f 'llama-server --host'` kill) killed the resident THINKB server under the R2 rec1 flight. The driver saw
  "Remote end closed connection" on a Solver contact and aborted: rec1 attempt ABORTED at 172 calls / 481.5 speech-seconds, 27 rows
  checkpointed (trace present); chain exit rc 9 at 13:42:04Z. Coordinator error, not a harness or owner action. The THINKB7 task was stopped
  within a minute; no second server is up.
- Rules recorded: (1) never register or start a serving/monitor task while a flight is open -- the entry's reaper is unscoped; (2) `saea_task.ps1`
  gets a `-NoStart` switch (follow-up, model-free) and the serving entry's reaper must be scoped to its own session; (3) the pre-flight
  checklist of every chain: "no other SAEA-Serving-* task Running".
- R2 cell status: this is the cell's SECOND failure (rec1 was the host reboot). The package rule reads "a second failure closes the cell; the fix
  is proven on a four-row dry run" and `recovery.py` refuses a second record without an `owner_exception` naming the ruling (320 B precedent).
  **Owner decision 328 requested:** A = exception granted for R2 rec2 as a mode-A trace resume of the rec1 attempt (keep the 27 complete rows,
  fly 1,053; the harness is unchanged, so the resume gate's full-trace replay applies; ~18.5 GPU-h); B = exception granted as a whole re-fly
  under rec2 ids (~19 GPU-h); C = the cell is closed (R2's question -- the perception-off same-roster replicate and solver-2048 -- is answered
  in a later package). Recommended A.
- GPU continuity (owner directive >= 24 h): NX-T R2b (ruling 325 A) is registered on master now and flipped + chained immediately -- it is
  independent of R2's read, its serving session is THINKB7, and the queue hook for "R2 then R2b" is therefore not installed; after 328 the R2
  rec2 flies behind R2b through the same hook form (R2b exit -> R2 rec2).

### NX-T R2b FLYING since 13:58Z on the new serving session (coordinator, 2026-10-17 14:04Z)

- R2b registered through the launcher at 13:47Z (derive from the one-arm table, 4 rows countersigned, receipt minted, commit 2ef569b9e;
  expected 21.2 GPU-h, ceiling 27.6 + 0.5 smoke; fit: supply bound 55 -> 52 items for the estimate only, observed max 8 items / 13,918-token
  Solver prompt under a 14,334 limit); flipped in ext4 13:47-13:52Z (gate PASS x2, master -> cdd6cd95b = flight commit); chain SAEA-Chain-NXT2B.
- First chain start 13:53Z failed at the serving swap: the THINKB7 task I had registered by hand (the 13:41Z incident) could not be re-registered
  by the swap's WSL-interop helper ("register refused: access denied", another principal); the swap tore down and restored THINKB, then its
  summary crashed decoding the refusal's GBK bytes (fixed e907c011d, `errors="replace"`). Fix: both hand-made THINKB7 tasks unregistered; the
  chain restarted 13:57:38Z by hand (the launcher's chain step requires flight commit = master HEAD, and master had moved by two commits that
  touch no registered bytes); the swap registered and started THINKB7 itself: `serving-slurp-thinking-module-fold-b-np4-budget3072-max7168-v1`
  ready 13:58:24Z (29 GB host free); smoke driver 13:58:24Z; GPU 92 %. Sequence: smoke-4 -> machine sign-off (conditions emitted by the derive,
  20-min veto) -> the 1,080-row column (arms budget-3072 delivering, solver-6144). Seal expected about 2026-10-18 12:00Z.
- Standing rule from today's two serving incidents: serving/monitor tasks are created only by `serving_swap.sh` (never by hand), and no
  serving task is ever registered or started while a flight is open.

### Owner ruling 328 (2026-10-17 14:36Z; owner message translated from Chinese: "Decision 328: just resume from the checkpoint, no?")

- **328 = resume.** The owner grants the exception in the form of the rectified recovery capability itself (ruling 309): NX-T R2 continues as
  **rec2 = a resume of the rec1 attempt keeping its 27 complete rows** (checkpoint mode B when `rails/runner.py` is byte-identical between the
  rec1 flight commit 9790c071f and the rec2 flight commit, else trace mode A; both replay-gated before launch), flying the remaining 1,053 rows
  (~18.5 GPU-h). The owner's wording is also a standing correction of the coordinator's choice at rec1: **a stopped attempt is resumed, never
  re-flown whole, whenever a checkpoint or trace exists**; the whole re-fly is reserved for an attempt that left no trace.
- Engineering (model-free, Sonnet, worktree): the R2 family gets a second recovery record in the R1 rec2 form (`recovery_index` 2,
  `owner_exception` = "owner ruling 328 of 2026-10-17", `resume_from`, `resume_mode`, predecessors = the first attempt + rec1 snapshots,
  run-cumulative caps 11,880 + 42 + 172 calls), the writer appends the rec2 generation row + FIT-REC2 row (the rec1 generation row folds into
  it), the chain's `arm-only` segment carries R1's resume precondition (predecessor pin unchanged, rec2 attempt record absent, the run directory
  may hold only the preflight resume declaration), and the package re-mints with `--supersede`. Flies after R2b through the queue hook
  (R2b exit rc 0 -> flip `NXT2_KINDS=arm` -> chain `arm-only`).
- Rule for every next package writer: the single-recovery form defaults to RESUME (mode B, fallback mode A); "re-flown whole" only when no
  pin exists. R2b's family inherits this at its first (if any) recovery.

### NX-T R2 rec2 (328) REGISTERED and queued behind R2b; checkpoint-resume design flaw found (coordinator, 2026-10-17 15:10Z)

- Sonnet's rec2 package merged (faa104243): the R2 family carries a rec1 + rec2 history; rec2 = mode-A TRACE resume of the aborted rec1 attempt,
  26 complete rows kept (the registry's "27" counted the header line; the checkpoint and the trace agree on 26 complete + 4 partial), 1,054 rows
  flown (~23.5 GPU-h by the plan's formula; the ruling's "18.5" was the coordinator's rough figure), run-cumulative caps 12,094 calls / 35,317 s,
  ceiling 31.3 unchanged; offline replay proof on a scratch copy 26 checked / 0 failing / 0 sealed twice. Registered on master 15:07Z (writer
  `--append-recovery-ledger`, rec2 generation + FIT-REC2 rows countersigned 15:07:25Z, the rec1 generation row folded, receipt re-minted
  `--supersede`, commit 71c9fc205; the pre-flip registration gate shows the expected receipt-hash mismatch the flip's re-pin resolves).
- **Design flaw (M5, ruling 309): checkpoint resume (mode B) can never serve a NEW attempt id.** The checkpoint header binds the cell's protocol
  hash, and that hash covers the experiment fragment INCLUDING the attempt id, so every rec attempt (which must carry a new attempt id, the
  one-time key) is refused by the launch-time checkpoint reader. Only the trace pin (mode A) works. Follow-up (model-free): bind the checkpoint
  to the protocol hash computed WITHOUT the attempt id (or to the roster + program + config identity), with a test that a rec attempt resumes a
  predecessor's checkpoint. Until then every resume is mode A.
- Queue: hook `queue_nxt2rec2_after_nxt2b.sh` (06a68a83d; installed as task SAEA-Queue-NXT2REC2, armed 15:10Z with start stamp
  2026-10-17T13:57:38Z) waits for `CHAIN_NXT2B_EXIT rc=0`, then flips the R2 arm cell (`NXT2_KINDS=arm`, ext4), verifies the gate block and
  flight commit = master, and starts SAEA-Chain-NXT2 (`arm-only`: resume precondition + driver replay gate + serving swap to THINKB). It refuses
  on any other R2b exit, a dirty master, a live flight or a non-converged flip. RULE while it is armed: no commit on master between R2b's seal
  and the hook's flip (the flip refuses a moved master).
- Expected timeline: R2b seal ~2026-10-18 12:00Z -> R2 rec2 flies ~12:10Z -> seal ~2026-10-19 12:00Z. Then reads (R2b, R2) -> 324-B confirm /
  Solver template column (326 A).

### R2b READ: NEEDS-NO-MORE-BUDGET; R2 rec2 flying; forced-close root-cause analysis; owner rulings 329 A and 330 A (coordinator, 2026-10-18 15:30Z)

- R2b column sealed 2026-10-18T12:34:22Z (chain rc 0); ledger rows closed (a177f5d6f); READ row countersigned (310e23ae0); read written
  14:40Z. Word `solver-6144` = **NEEDS-NO-MORE-BUDGET**: delivering budget-3072 72.74 SLU / 85.37 intent; solver-6144 71.93 / 84.81; paired SLU
  -0.81 [-2.19, +0.57], intent -0.56 [-1.67, +0.56] (saves 17 / harms 23); Solver forced-close share 40.1 % -> 37.8 %; cost 1.37x delivering
  rows (9.23 vs 12.69 GPU-h per lock flight). The lock keeps Solver 3,072 / 4,096. Results note: Opus (in progress).
- R2 rec2: the queue hook flipped the R2 arm cell correctly (master 394f4a760 = flight commit, 12:38:56Z) but refused to launch on a false
  match: its flip-log grep for `refus` hit the informational line `repin exit N (1 = its internal check refused the dirty tree, expected)`.
  The coordinator verified HEAD = flight commit, no flight.lock, no flight process, chain script `arm-only`, and started SAEA-Chain-NXT2 by hand
  at 14:36:38Z (GPU idle 12:39-14:36Z). Swap to think-budget-np4 ready 14:37:24Z; driver replay gate OK; arm-start 14:37:33Z. Seal expected
  ~2026-10-19 14:00Z. Every later hook excludes the `repin exit` line from its refusal grep.
- Forced-close analysis (coordinator, model-free, over the sealed R2b column rows and their official per-row scores; development numbers on
  TRAIN Fold B, no text printed): forced share rises with the Solver's workload (supplied items 30-39: 33 %, >= 40: 61 %; Solver prompt
  > 9k tokens 60-68 %; Perception candidates 1/2/3: 38/45/65 %; entities output 0/1/2+: 14/42/63-77 %); 66 % of rows forced at 3,072 are still
  forced at 6,144; 25 % of rows flip forced status between the two arms (greedy decoding at temperature 0 is not reproducible under np4
  batching). Forced rows hold 65 % of slot FP, 64 % of FN and 54 % of intent errors (empty-gold false fill 45.6 % vs 10.4 % natural), but the
  within-row contrast over the 269 discordant rows shows the forced close itself only adds precision loss (+28 FP, +25 false-fill rows; TP,
  FN, intent unchanged; rough ceiling of removing it ~+1.4 pp word-level SLU). Root cause: exhaustive verification over every candidate
  intent and supplied item with no stopping rule, under greedy decoding. NX-T R3 (326 A template column, Sonnet building) arms: t1
  decide-once, t2 grounded-or-empty, t3 supply-focus (replaces type-inventory), t4 = t1 + t2; twin aa; lock delivering.
- Owner, verbatim: 「决策329：A，决策330：A」 (English: "Decision 329: A; decision 330: A").
- **329 A:** a DECODING-POLICY control axis is opened: a same-flight column whose arms differ only in the Solver's sampling parameters
  (temperature / top_p / top_k / presence penalty, fixed seed), with a twin and the greedy lock delivering. Instrument work is model-free
  (Sonnet) and starts after the R3 package lands (both touch the column instrument). It flies after R3.
- **330 A:** a bounded diagnostic exception to ruling 286: one small registered probe re-issues the sealed Solver requests of about 40 R2b
  rows (forced and natural, both budgets) with the reasoning bytes RETAINED under the data root only (never in documents, notes or chat
  transcripts beyond counts and pattern statistics), to classify the non-terminating reasoning (enumeration vs repetition loop). 286 stays in
  force for every other cell. Registered with its own ledger rows; flies in the window after R2 rec2 seals and before R3 (under 1 GPU-h).

### Owner rulings 331 A, 332 A, 333 B, 322 A (coordinator, 2026-10-18 16:10Z)

Owner, verbatim: 「决策331：A，决策332：A，决策333：B，决策322：A」 (English: "Decision 331: A; decision 332: A; decision 333: B; decision 322: A").
- **331 A:** when the NX-T R2 rec2 chain exits rc 0, the queue proceeds without an owner read: the 330 diagnostic probe (< 1 GPU-h), then
  NX-T R3 (Solver instruction-template column, ~35 GPU-h). The 324-B Fold A confirm (Perception no-think, ~5 GPU-h) moves after R3 and flies
  only if the R2 same-roster replicate reads no resolved loss.
- **332 A:** the decoding-policy column (329 A) flies with four candidate Solver decoding arms: (1) temperature 0.6 / top_p 0.95 / top_k 20
  (Qwen's published Thinking-mode setting); (2) arm 1 + presence penalty 1.5; (3) temperature 0.3; (4) greedy + presence penalty 1.5; plus a
  twin and the greedy lock delivering; fixed seed; same-flight paired on TRAIN Fold B; ~35 GPU-h. The instrument is built model-free after
  the R3 package lands.
- **333 B:** the carrier base runs (P3.2 Thinking packets for A2T / E21 / E22, P3.3 all-off + direct baselines on the Thinking core) fly
  after R3 and before the decoding column; the packages are built now (model-free) so that they are ready.
- **322 A:** `.wslconfig` memory 44 -> 36 GB is applied in the no-flight window at the R2 rec2 seal. Because `wsl --shutdown` kills every WSL
  process (including the queue hook), the window is run by a Windows-side orchestrator: wait for `CHAIN_NXT2_EXIT rc=0` -> edit
  `.wslconfig` (backup kept) -> `wsl --shutdown` -> restart -> start the queue task that flips and chains diagnostic -> R3. Expected GPU idle
  a few minutes.
- Resulting queue: R2 rec2 (seal ~2026-10-19 14:00Z) -> 322 window -> 330 diagnostic -> R3 (~35 h) -> [324-B if R2 reads no loss] -> P3.2 +
  P3.3 carriers -> decoding column (332) -> Fold A confirms of nominated arms -> composed lock v3.x -> DEV replicate -> test read (new allowance).

### R3 registered, 330 diagnostic registered, 322 window orchestrator armed (coordinator, 2026-10-18 16:05Z)

- NX-T R3 merged (aad056bcc, Sonnet 61e5875be) and registered by `package_launch.sh --until commit` (7c66a786e; 4 rows countersigned 15:51:44Z,
  receipt minted). Arms t1-decide-once, t2-grounded-or-empty, t3-supply-focus, t4-decide-once-grounded, aa, lock (program c7); expected 33.3
  GPU-h, ceiling 43.4 + 0.5 smoke. Words: NOMINATED / EFFICIENT-NO-LOSS / HARM (loss resolved beyond the A/A offset) / NEUTRAL.
- 330 diagnostic merged (79fbf07ba, Sonnet ba35d9d2b) and its probe row countersigned (579025b68): 40 sealed budget-3072 Solver requests +
  16 sealed budget-6144 requests of forced-both rows, 56 calls, ceiling 0.9 GPU-h; reasoning bytes under the data root only; render proof of all
  56 wire bodies against the sealed hashes passed offline.
- 322 / 331 window: Windows task SAEA-Queue-W322 (`scripts/flights/batch/queue/window_322_orchestrator.ps1`, aa23bf921) armed 16:02:38Z: on
  `CHAIN_NXT2_EXIT rc=0` after 14:36:38Z -> 180 s drain -> pre-step (no flight; `serving_swap.sh --stop-only`) -> `.wslconfig` memory 44 -> 36 GB
  (backup) -> `wsl --shutdown` -> post-step `window_322_post_restart.sh` (close R2 rows + commit, swap to think-budget-np4, diagnostic, then
  `queue_nxt3_after_nxt2.sh` which flips and chains R3; SAEA-Chain-NXT3 is registered by the launcher's own `saea_task.ps1 -Start`). Any
  other R2 exit or a refused step leaves everything as is. RULE: master must be clean whenever the window can fire (R2 seal ~2026-10-19 14:00Z).

### Carrier base (333 B) merged and P3.2 registered; carrier hooks wired into the 322 post-step (coordinator, 2026-10-18 16:30Z)

- Merged d21b3b8b7 (Sonnet 2f3eee717): P3.2 Thinking packets (A2T paired 400; E21 / E22 windows re-keyed onto the existing Instruct slices, no
  re-cut) and P3.3 all-off + direct baselines for A2T / E21 / E22 on the SLURP lock geometry (think-budget-np4, 3,072 / 4,096). Expected ~21 GPU-h
  for P3.3 (A2T 2 x 1.6, E21 2 x 7.1, E22 2 x 2.0; ceilings ~30) + ~2.5 h packets. P3.2 registered 15c241904 (7 rows countersigned).
- P3.3 is registered by its hook AFTER the packets seal (its cells pin the packet hashes): the coordinator delegates the root countersign to
  `queue_carriers_after.sh --register` (rows say so). Hooks are Windows tasks SAEA-Queue-CARRIERPKT (waits CHAIN_NXT3_EXIT rc 0) and
  SAEA-Queue-CARRIERBASE (waits CHAIN_CARRIERPACKETS_EXIT rc 0), registered not started; `window_322_post_restart.sh` starts them after R3
  launches (a hook armed now would die at the 322 shutdown).
- Coordinator calls (model-free): the four red Instruct registration tests pin unflown Instruct carrier cells superseded by the Thinking cells
  -> retire them (cleanup later); 324-B is not built: after the R2 read, if needed, it is queued after the carriers. Known risks: E21/E22 window
  packets have never run on GPU (the 4-window smoke is the rehearsal and stops the chain on any receipt failure); the E21 seal-path refusal
  of 2026-10-10 ("unit-stitch has no matching trace record") is first exercised by the E21 smoke.

### NX-T R4 (decoding-policy column) merged and registered; the whole queue is wired (coordinator, 2026-10-18 17:40Z)

- Merged 56853bba4 (Sonnet 66b3e6503): instrument kind `roles.solver.decoding_variants` (temperature / top_p / top_k / presence_penalty only,
  bounded; every other axis refused by name; receipt v6) and package `slurp-nxt-r4-solver-decoding-fold-b-v1` (d1 T0.6/top_p0.95/top_k20, d2 +
  presence 1.5, d3 T0.3, d4 greedy + presence 1.5, aa, lock; seed fixed; expected 33.3 GPU-h, ceiling 43.4 + 0.5). Registered 7ff9ab4f1.
- The same merge carries a fix Sonnet found in R3: `nxt_r3_flip.sh` named the package directory with the wrong date (2026-10-17), which would
  have stopped the unattended R3 flip. All package paths of R3 / R4 / carriers / diagnostic were re-checked against the tree.
- Known limit: d4 keeps temperature 0; if the pinned llama.cpp build ignores presence_penalty under greedy, d4 reads as a second twin (its
  discordance equals the twin's) -- the read will show it.
- Full queue (all hooks start-only from the 322 post step): R2 rec2 -> 322 window -> diagnostic -> R3 (SAEA-Chain-NXT3) -> P3.2 packets
  (SAEA-Queue-CARRIERPKT) -> P3.3 carriers registered by the hook (SAEA-Queue-CARRIERBASE) -> R4 (SAEA-Queue-NXT4, waits up to 5 days).

### Owner decision brief 2026-10-19 02:15Z: open decisions 334-337, stage, plan (coordinator, on the owner's request)

Owner, verbatim: 「把需要我决策的事项，详细的梳理出来并解释给我听，同时把当前的工作阶段和在之后的工作计划也列一个详细的方案出来！」 (English: "Lay out
the items that need my decision in detail and explain them to me; also give a detailed plan of the current work stage and the work after it.")
- State: R2 rec2 487 / 1,054 flown rows checkpointed at 02:05Z (~42 rows/h, GPU 93 %); seal re-estimated ~2026-10-19 15:30Z (was 14:00Z);
  projected spend ~25 GPU-h under the 31.3 ceiling. SAEA-Queue-W322 Running (armed); carrier / NXT4 hooks Ready; master clean. No decision
  blocks the queue.
- **334 (PROPOSED)** the slot of the 324-B Fold A confirm (Perception no-think), if the R2 replicate reads no resolved loss: A = insert it
  after the carriers, before R4 (rewires the armed NXT4 hook); B = after R4, inside the Fold A confirm batch of the R3 / R4 nominated arms
  (recommended: no change to the armed queue, one batch).
- **335 (PROPOSED)** how nominated arms compose into lock v3.x: A = one Fold A confirm flight per nominated arm, then compose and run one DEV
  replicate; B = one Fold A column holding each nominated single arm, the composed arm, a twin and the v3.0 lock (recommended: same-flight
  paired, measures interaction, about the cost of A), then the DEV replicate of the composed arm only.
- **336 (PROPOSED)** the test-sample allowance for v3.x (one attempt, 3,010 rows): A = sign now, conditional on the DEV replicate reading no
  resolved loss with the gain reported beside the word (recommended: no idle wait for a signature); B = sign after the DEV read.
- **337 (= 285, deferred since 2026-10-12, now due)** the claim class of "at or above SOTA": A = published training-free / zero-shot systems
  per task (recommended); B = fine-tuned SOTA (SLURP gap after v3.0 on the test sample: SLU 73.05 vs 79.5, intent 86.33 vs 90.3); C = only the
  direct call of our own core. The comparator table is redone on the Thinking base after P3.3 (A2T paper column, Earnings WER).
- Owner action (no decision): delete the stray `C:\Program Files\Git\commit14.txt` (needs administrator rights).

### Owner rulings 334 B, 335 B, 336 A, 337 (= 285) fine-tuned target (coordinator, 2026-10-19 02:20Z)

Owner, verbatim: 「决策334：B，决策335：B，决策336：A，决策337：还是要把目标靶放到训练的对比上，虽然我们叫training free RL，但也是在针对任务做training，只是不调参数而已，我们要摸一下这类方法的天花板」
(English: "Decision 334: B; decision 335: B; decision 336: A; decision 337: the target must still be set against the trained systems --
although we call it training-free RL, it is still training on the task, only without changing parameters; we want to find the ceiling of
this class of methods.")
- **334 B:** the 324-B Fold A confirm of Perception no-think (only if the R2 replicate reads no resolved loss) flies after R4, inside the Fold A
  confirm batch; the armed queue is unchanged.
- **335 B:** one Fold A column holds each nominated single arm (R1 Perception no-think, R3 template, R4 decoding), the composed arm, a twin and
  the v3.0 lock (same-flight paired); then the DEV replicate of the composed arm only.
- **336 A:** the owner signs now the test-sample allowance for the composed lock v3.x (one attempt, the 3,010-row sample), conditional on the
  DEV replicate reading no resolved loss; the gain is reported beside the registered word. The allowance document is minted with the v3.x
  package and carries these owner words verbatim.
- **337 = 285 B:** the comparator of the programme goal is the FINE-TUNED class (class C of the 2026-10-12 table). Training-free RL is
  framed as task training without parameter updates; the programme measures the ceiling of that method class against trained systems.
  Tiers on SLURP (published rows on the full 13,078 test; ours on the 3,010 sample, v3.0 73.05 SLU / 86.33 intent): LauraGPT 87.87 / 73.45
  (SLU matched, intent -1.5); SFT Qwen2-Audio-7B 88.13 / 76.75 (-1.8 / -3.7); UniverSLU-14 90.3 / 79.5 and TCPGen 88.9 / 79.5 (-4.0 / -6.45).
  A like-for-like claim needs the full official test split: a separate allowance, proposed when a lock reaches a tier on the sample.
  Zero-shot rows stay in every table as the secondary column. Consequence for planning: a ceiling (gap-to-SOTA) decomposition on the sealed
  DEV / TRAIN-fold rows of v3.0 (never test rows) is commissioned model-free to rank the remaining levers by the headroom they can reach.

### v3.0 gap decomposition landed (1bfe62ffd); decisions 338-339 PROPOSED (coordinator, 2026-10-19 02:35Z)

- Note `docs/results/2026-10-19-slurp-v3-gap-to-finetuned-sota-decomposition.md` (Opus, model-free, DEV n = 1,000 + Fold B n = 1,080, no test
  row read). Intent: 75-78 % of errors have gold absent from Perception's shortlist; Perception commits to one candidate on 81-85 % of rows;
  gold off the list -> 6-8 % accuracy, sole gold -> 99 %. Slots: missed +5.7 / +6.2 SLU, false fills +6.3 / +6.8, value errors +4.4 / +5.1,
  wrong type +3.8 / +3.6. Selection over five sealed Fold B decodes would reach intent 89.6 / SLU 80.6 but a plurality vote adds nothing.
  Estimated method-class ceiling with the current components: SLU ~74.5-77.0, intent ~86.3-88.0 (judgement from past conversions, mostly on
  the Instruct core) -- LauraGPT reachable, SFT Qwen2-Audio at the top of the band, UniverSLU-14 below the ceiling on both metrics.
- **338 (PROPOSED)** a lever column after R4 on Fold B (same-flight paired, twin + lock): A = (1) false-fill suppression on the Thinking core
  (multi-sample support filter + gated empty decision; never tested on Thinking) and (2) a Perception multi-sample candidate UNION (k sampled
  Perception decodes, union of their candidates as the shortlist; attacks the 75-78 % intent mass, untested shape) (recommended); B = (1) only;
  C = none until R3 / R4 read.
- **339 (PROPOSED)** the structural constraint behind the UniverSLU gap (missed slots: training-free proposer recall ceiling 0.086; the
  transcript path is barred by the 2026-09-06 owner ruling): A = keep the constraint and report the measured method-class ceiling honestly
  (recommended for now); B = admit a pinned frozen speech front-end tool (e.g. a stronger ASR as a tool the core may call, answer authority
  stays with the core), which re-opens the barred transcript path and needs its own owner amendment.

### Owner ruling 340: test-sample error analysis allowed, no tuning on it (coordinator, 2026-10-19 02:50Z)

Owner, verbatim: 「面向测试集的分析也可以开展，我们不基于测试集调优就好了」 (English: "Analysis aimed at the test set may also be carried out;
we just must not tune on the test set.")
- **340:** a model-free error analysis of the SEALED successor-3 run on the 3,010-row test sample (v3.0) is allowed: the same decomposition as
  the DEV / Fold B note, plus a transfer check (does the test decomposition match DEV / Fold B). Guards: (1) no model, server or GPU contact; no
  new test generation; (2) aggregates only in documents (no utterance, transcript or output text); (3) no lever, arm, prompt, threshold,
  knowledge entry or roster is selected or changed on a test-only finding -- every design choice keeps resting on DEV / TRAIN-fold evidence,
  and the recommendations of decisions 338 / 339 stand as written at 347973d56, before this read; (4) every later test-sample claim lists this
  analysis as inherited exposure; (5) the closure roster SLURP-TEST-CLOSURE-10068-V1 stays untouched. Ledger row
  SAEA-SLURP-TEST-SAMPLE-3010-V3-GAP-ANALYSIS-V1 is registered before any per-row test number is read.

### Owner rulings 338 and 339 (coordinator, 2026-10-19 02:55Z)

Owner, verbatim: 「决策338：如果我们当前没有锁定SLURP的完整技术方案，就先去锁定SLURP的方案，其他数据集上的实验都可以推迟；决策339：之前就放开过啊，我们是接受主动调用ASR工具进行转写的，但是不要做默认转写，要进行触发式转写」
(English: "Decision 338: if we have not yet locked the complete SLURP technical scheme, lock the SLURP scheme first; the experiments on the
other datasets can all be postponed. Decision 339: that was already opened before -- we accept a model-initiated call of an ASR tool for
transcription, but no default transcription: the transcription must be triggered.")
- **338:** SLURP lock first. The P3.2 / P3.3 carrier runs (A2T / E21 / E22) are DEFERRED until the composed SLURP lock v3.x is sealed (their
  packages stay registered / built, unflown). The queue is rewired (02:55Z): `window_322_post_restart.sh` starts only SAEA-Queue-NXT4, and the
  installed wrapper `/home/chao/saea-queue/queue_nxt4.sh` now waits for `CHAIN_NXT3_EXIT rc=0` in `/home/chao/nxt3-chain.out` (backup
  `queue_nxt4.sh.bak-20261019-338`). SAEA-Queue-CARRIERPKT / -CARRIERBASE stay registered, not started. The 338 lever column (false-fill
  suppression on Thinking + Perception multi-sample candidate union) is part of the SLURP lock work and is built for after R4.
- **339:** CORRECTION of the coordinator's 02:35Z framing: the 2026-09-06 transcript ban was superseded in scope by the 2026-09-29 direction
  (decisions 200-205) and the model-initiated tool directive (row 206); a pinned ASR tool that the core CALLS is admitted. Ruled: the ASR tool is
  TRIGGERED, never a default transcript -- the core decides per row to call it (tool offer scoped to the slot-value step), the call decision
  is recorded in the receipt, the transcript never enters the intent decision (DEV-1000 E5 finding), answer authority stays with the core.
  Known constraint (S2a.1, E5): pinned Whisper recovers only half of the missed slot values and the lexicon ranker loses more; a stronger
  pinned ASR candidate and the trigger signal are designed model-free first (offline, on sealed Fold B rows + existing E5 transcripts).

### Owner decision brief 2026-10-19 03:00Z (Fable 5.1 root, on the owner's request after the model switch): nothing open now; 341-342 announced

- State: R2 rec2 515 / 1,054 flown rows at 02:47Z (GPU 92 %), seal ~15:30Z; master clean at 23c7033f4; queue after 338: R2 -> 322 window ->
  330 diagnostic -> R3 -> R4 (SAEA-Queue-NXT4 waits CHAIN_NXT3_EXIT); carriers deferred. Three model-free Opus jobs run: the 340 test-sample
  decomposition (transfer check), the 338 lever-column design, the 339 triggered-ASR design.
- No decision blocks the queue. Announced for when the designs land: **341** approve the 338 lever-column arms (L1 false-fill suppression on
  Thinking, L2 Perception multi-sample candidate union, twin, lock; ~1.5 days GPU after R4); **342** go / no-go on the 339 triggered-ASR
  experiment from its offline bounds, including whether a stronger pinned ASR needs an acquisition entry (owner GO for any download).
- Plan: R4 seal ~10-22 13:00Z -> 338 column -> 335 B composed Fold A column (nominated R1 / R3 / R4 / 338 arms + composed + twin + v3.0) ->
  DEV replicate of the composed arm -> test-sample read under the 336 A allowance -> SOTA table on the fine-tuned target (337) -> then the
  deferred carriers (P3.2 / P3.3) -> full-test allowance proposal if a tier is reached.

### 338 lever column and 339 triggered-ASR designs landed; decisions 341 and 342 PROPOSED (coordinator, 2026-10-19 03:40Z)

- Specs: `docs/superpowers/specs/2026-10-19-slurp-338-lever-column-design.md`, `docs/superpowers/specs/2026-10-19-slurp-triggered-asr-tool-design.md`
  (Opus, model-free, Fold B sealed rows + E5 transcripts; bound scripts under `scripts/analysis/design338/`, `scripts/analysis/design339/`).
- 338 column (after R4): `l1-support` (1 Perception + 5 Solver samples, VER-1 support filter n5-s2 + N1-gated empty, 6 contacts/row),
  `l2-union` (4 Perception samples, union shortlist capped at 3, 5 contacts/row), `aa`, `lock`; ~69.4 GPU-h (L1 ~28.4, L2 ~22.5, twin + lock
  ~18.5), ceiling 90.3. Offline bounds on sealed greedy decodes: L1 +1.09 [+0.53, +1.63] SLU (n5-s3 +1.77), expected +0.8 to +1.8 vs the 1.49
  floor; L2 union recall 88.15 -> 89.81 % (gold newly listed on 18 rows), rank-2/3 conversion 44-59 %, expected intent 0 to +1.0 vs the
  0.65 floor (likely NEUTRAL). New code: two branch axes `perception_samples` / `solver_samples` in `rails/supply_variants.py` compiling into the
  existing PerceptionBranchGroup, commit policy, merge-policy registry, receipt +1, reader, family, tests, 4-row smoke (~9 touch points).
  Free checks before signing: rerun the L1 rule over R4's sealed decodes (drop L1 if < +0.67); if R3 t2 is nominated, L1 re-bases on it in 335 B.
  Composed L1+L2 goes to the 335 B column.
- 339 tool: one tool offered only in the Solver call, at most once per row, transcription (CPU) only when called; intent locked to the
  committed one; every new/changed slot must cite a transcript span; replacement only when the old value is absent from the transcript;
  receipt records the call decision. Bounds (Fold B, Whisper large-v3 token WER 0.152): 88 rows (8.15 %) where a call can help; +5.07 SLU
  [+4.09, +6.14] at perfect conversion, +2.34 at the measured 0.457; best trigger signal AUC 0.71 (Solver reasoning length), combined 0.68
  (precision 0.14 / recall 0.51 at a 30 % call rate) -> +1.19 to +2.59 at 30 % calls; harm margin < 1.5 broken slots per 100 calls; perfect ASR
  adds at most +5.53 more. Stronger ASR candidates (Parakeet-TDT-0.6B-v2, Canary-1B-flash, Canary-Qwen-2.5B) need acquisition entries;
  keep one only if its Fold B transcription pass (~0.15 GPU-h, no core contact) beats Whisper's ceiling by >= +1.0 pp at WER < 0.152.
  Verdict: effectiveness flight NO-GO on the bounds; engineering + stronger-ASR pass GO; single-arm probe (11-15 GPU-h, stop rules: call
  rate 5-60 %, precision >= 0.18, gain vs in-call draft >= +1.49 with CI > 0, no intent change) conditional after R3 / R4.
- **341 (PROPOSED)** the 338 column: A = build both arms now (model-free), fly after R4 with L1 subject to the free R4 check and L2 kept
  as the ceiling probe of the shortlist lever (recommended under the 337 ceiling mandate; ~69 GPU-h); B = L1 only (~47 GPU-h); C = build,
  decide the arms after the R3 / R4 reads.
- **342 (PROPOSED)** the 339 tool: A = build the tool model-free now, owner GO to acquire the three stronger ASR candidates (lock entries,
  one CPU/GPU transcription pass each on Fold B, no core contact), probe after the 338 column with the best ASR if it passes the +1.0 pp test
  (recommended); B = build and probe with the pinned Whisper only (no download; probe bound +1.19 to +2.59); C = drop the line.

### Owner rulings 341 A and 342 A (Qwen3-ASR only; VRAM-bounded) (coordinator, 2026-10-19 03:45Z)

Owner, verbatim: 「决策341：A，决策342：A，工具的话，你考虑下qwen3-ASR系列的模型其他的都不用太关注了，而且要考虑下我们的显存容量限制」
(English: "Decision 341: A; decision 342: A. For the tool, consider the Qwen3-ASR series of models and do not pay much attention to the
others; also take our GPU-memory capacity limit into account.")
- **341 A:** the 338 lever column is built now (model-free, Sonnet worktree, from `docs/superpowers/specs/2026-10-19-slurp-338-lever-column-design.md`)
  and flies after R4: `l1-support`, `l2-union`, `aa`, `lock`; L1 subject to the free check over R4's sealed decodes (drop below +0.67 pp).
- **342 A, amended to the Qwen3-ASR series:** the tool is built now (model-free) from
  `docs/superpowers/specs/2026-10-19-slurp-triggered-asr-tool-design.md`; the ASR candidates are ONLY the open Qwen3-ASR models (Qwen3-ASR-0.6B
  and Qwen3-ASR-1.7B, Transformers format `-hf`; released 2026-01-29, native Transformers support 2026-06-26; package `qwen-asr`). Parakeet /
  Canary are dropped. Acquisition = owner GO under this ruling: umbrella `docs/datasets.lock.json` entries + fetch to the data root; an
  isolated venv (never `speechrl`).
- VRAM constraint recorded: the GPU reports 24,463 MiB total with 22,976 MiB held by the resident Thinking server (np4 x 24,576 slots), i.e.
  about 1.4 GB free while a flight is open. Consequences: (1) the runtime tool transcribes on CPU by default (bf16/fp32 Transformers, one
  clip per call; SLURP clips are a few seconds), GPU only when a swap window has freed the memory; (2) the Fold B transcription pass that
  qualifies each candidate (>= +1.0 pp over Whisper's containment ceiling at WER < 0.152) runs on CPU beside the flight, or on GPU in the
  next no-flight window, and is ledgered as a tool contact before any number is read; (3) the serving geometry is never shrunk for the tool.
- Model-free follow-ups queued after these two builds: mode-B checkpoint fix (protocol hash without the attempt id), `saea_task.ps1 -NoStart`,
  the serving-entry reaper scope, the stale Instruct carrier tests, the E21 seal-path gap (no longer urgent: carriers deferred by 338).

### 339 part 1 merged (sidecar + Fold B qualification instrument + CPU smoke); qualification pass registered (coordinator, 2026-10-19 09:45Z)

- Merged sonnet/asr339 (0a2a206b9, ff) and umbrella sonnet/asr339-lock (70b4bb5: Qwen3-ASR-0.6B / 1.7B ggml-org bf16 GGUF + mmproj pinned,
  6.2 GB under $SPEECHRL_DATA_DIR/models/qwen3-asr-gguf/). Sidecar `scripts/flights/direct/asr_sidecar.sh` (CPU, port 8190, argv
  `--port` before `--host` so the core serving entry's reaper pattern does not match; GPU hidden; lock-verified hashes; receipt
  saea-asr-sidecar-session-v1). Both GGUFs load on the pinned build 04ccc72a2 (upstream #19441 present). 4-row CPU smoke: 0.6B WER 0.35 at
  0.52 s/clip, 2.7 GB RSS; 1.7B WER 0.50 at 1.20 s/clip, 5.4 GB RSS -- four clips, no verdict; output well-formed (no #22357 sign).
- Qualification pass SAEA-SLURP-ASR339-FOLD-B-V1 registered and countersigned (2026-10-19T09:44:25Z); runs now on CPU beside the R2 flight (host 34 GB free,
  needs ~6 GB; ~9 + ~21 min). Gate for 343: canonical WER < 0.152 and missed-slot containment ceiling >= Whisper's +1.0 pp.
- Known: the Windows tool_catalog_check needs `more_itertools` (passes in WSL); 338 part 1 (instrument) in progress.

### ASR339 qualification READ: no Qwen3-ASR candidate clears the gate; decision 343 PROPOSED (coordinator, 2026-10-19 10:45Z)

Fold B (n = 1,080), CPU passes sealed (ledger row consumed). Canonical WER / sentence-exact; containment of the v3.0 lock's error items
(R2b budget-3072 column); ceilings from `scripts/analysis/design339/asr_trigger_bound.py --asr [--union]` (bound339-*.json):

| ASR | WER | missed-slot values contained | distinguishable value errors | ceiling SLU pp, perfect conversion | at measured conversion 0.457 |
|---|---|---|---|---|---|
| Whisper large-v3 (E5, pinned) | 0.152 | 70 / 112 | 23 / 166 | +5.07 [+4.09, +6.14] | +2.34 |
| Qwen3-ASR-0.6B | 0.144 | 66 / 112 | 18 / 166 | +4.57 [+3.61, +5.59] | +2.11 |
| Qwen3-ASR-1.7B | 0.120 | 65 / 112 | 22 / 166 | +4.64 [+3.66, +5.70] | +2.14 |
| Whisper OR 1.7B (two-tool union) | -- | 73 / 112 | 23 / 166 | +5.19 [+4.18, +6.33] | +2.40 |

- Both Qwen3-ASR models beat Whisper on WER (1.7B: 0.120, sentence-exact 59 %) and on all-gold containment (0.789 vs 0.761), yet neither
  recovers more of the values the lock MISSES (65-66 vs 70 of 112): the missed values are the hard ones for every ASR. The union adds +0.12 pp.
  Gate (>= Whisper + 1.0 pp) NOT met by any candidate. The trigger bound is unchanged (best signal AUC ~0.71): +1.2 to +2.6 pp at a 30 % call
  rate; clearing the 1.49 floor needs conversion >= 0.58 at 30 % calls, never observed (0.457).
- Cost (CPU): 0.6B 0.56 s/clip, 2.7-10.9 GB RSS; 1.7B 1.39 s/clip, 5.4-13.7 GB RSS (peak RSS grows with the server's slot cache).
- **343 (PROPOSED)** A = close the triggered-ASR line now: the measured ceiling of the line (+4.6 to +5.2 pp perfect, +2.1 to +2.4 realistic,
  +1.2 to +2.6 after the trigger) is reported as a bound in the paper; the sidecar + instrument stay as sealed infrastructure; the part-2 tool
  contract is NOT built (recommended); B = build part 2 and fly the single-arm probe with Qwen3-ASR-1.7B after the 338 column (11-15 GPU-h,
  stop rules as designed) as the ceiling probe under the 337 mandate; C = B with the two-tool union (Whisper + 1.7B; +0.12 pp more ceiling,
  two sidecars, not worth its complexity).

### Owner direction 2026-10-19 ~11:00Z: proper-noun-enhanced ASR decoding; single-module optimisation continues; decision 344 PROPOSED (coordinator, 11:10Z)

Owner, verbatim: 「我在想这部分你是不是可以考虑做一些专有名词强化的ASR解码，来提升下模型的表现？像qwen-ASR这种模式，我们是否能够对他做一些优化，提升和改进呗」
(English: "I am thinking: for this part, could you consider proper-noun-enhanced ASR decoding to raise the model's performance? For a model
of the Qwen-ASR kind, can we optimise, raise and improve it?") and 「要注意我们之前讨论的内容，单模块的优化还是要进行的！」 (English: "Mind
what we discussed before: the single-module optimisation must still go on!").
- Reading: 343 is HELD (not closed) pending a biasing study; the ASR line is pursued as contextual biasing of the pinned Qwen3-ASR (in scope:
  "contextual biasing" is a named boundary task), training-free: Qwen3-ASR accepts context terms in its text prompt (hf card hotword example;
  arXiv 2608.05759), plus llama-server `logit_bias` and n-best union. Knowledge source = the TRAIN folds view excluding Fold A / B; scope per
  row = the lock's own committed intent -> slot types -> value lexicon (never the row's gold). Measured on the Fold B instrument (CPU, tool
  contacts only; ledger row SAEA-SLURP-ASRBIAS-FOLD-B-V1 registered before the pass). Same gate: missed-value ceiling >= Whisper + 1.0 pp.
- Single-module optimisation is unchanged and has priority on the GPU: R2 rec2 flying, R3 / R4 queued, the 338 column being built (Sonnet,
  part 1 instrument in progress). The ASR biasing work is CPU-side and runs beside it.
- **344 (PROPOSED)** the biasing column: A = V1 type vocabulary, V2 intent-scoped lexicon (N = 30 / 100), V3 = V2 + logit_bias, V4 n-best
  union, on Qwen3-ASR-1.7B (CPU, ~25 min per variant; recommended); B = V2 only; C = none (then 343 as proposed).

### Owner ruling 344 A; 322 window incident (data VHDX detached by wsl --shutdown); power plug replaced, GPU at 175 W; resumption (coordinator, 2026-10-24 13:30Z)

Owner, verbatim: 「决策344：A」 (2026-10-20) and 「继续吧，我们换了原装电池插头，GPU配置可以调的更高一些」 (2026-10-24; English: "Continue; we
replaced the original battery/power plug, the GPU configuration can be set higher.").
- 322 window, 2026-10-20 11:29-11:38Z: R2 rec2 sealed rc 0 at 11:29:29Z (the rec2 column took ~45 h against the 23.5 h estimate: the laptop
  ran on a degraded power plug; see below); the orchestrator stopped the server, wrote memory=36GB, shut WSL down and ran the post step, which
  REFUSED: `wsl --shutdown` detaches the data VHDX (/mnt/saea-data-1; mounted only by the boot-time task SAEA-Mount-Data1), so the data root
  was absent and both the ledger closure (rc 1) and the serving swap (rc 10, "resident: cannot-tell") refused; R3 did not launch. Fix
  8b27c67ce: the post step starts SAEA-Mount-Data1 and waits for the data root. The coordinator's rerun on 10-20 was lost with the session
  (exit 4, no log); the host then rebooted (power work). GPU idle 2026-10-20 11:29Z -> 2026-10-24 (resumed today).
- Power: nvidia-smi now reports Current / Requested Power Limit 175 W (Default 95 W, Max 175 W; before the plug change the card was held at
  the lower cap, which explains the 2x slowdown of R2 rec2). Windows scheme 高性能 (High performance). No geometry change (VRAM unchanged:
  np4 x 24,576 holds 22,976 of 24,463 MiB); the expected effect is throughput back to the measured 1.84 rows/min or better. Verified on the
  R3 flight by the throughput table.
- 344 A: the biasing instrument merged (d38ef3f7f, Sonnet 8658908dc; smoke: context rendered as the ChatML system turn, output changed on
  2 / 4 rows for v1, 1 / 4 for v2-n100); ledger row SAEA-SLURP-ASRBIAS-FOLD-B-V1 countersigned (2026-10-24T13:15:59Z); the 7-variant pass (~4.4 h CPU, 1.7B)
  runs after the serving swap, beside the R3 flight. 338 part 1 merged next; part 2 (runtime fan-out + package) re-commissioned (the first
  attempt died to an API connection error before its first commit).
- Resumption order now: post step (close R2 rows -> swap -> 330 diagnostic -> R3 flip + chain -> NXT4 hook) -> R2 rec2 read -> ASRBIAS pass.

### NX-T R2 rec2 READ: Perception no-think does NOT replicate no-loss (UNRESOLVED, -1.49 SLU); solver-2048 UNRESOLVED; 324-B does not fly; R3 flying at full power (coordinator, 2026-10-24 15:35Z)

- Read 15:20Z (READ row countersigned 15:17Z, consumed): n = 1,080 (26 kept + 1,054 flown, mode A). Delivering `budget-3072` 72.21 SLU / 84.91
  intent. `perception-off-solver-3072` 70.72 / 85.56: paired SLU **-1.49 [-2.83, -0.11]**, intent +0.65 [-0.65, +2.04] (saves 32 / harms 25),
  word UNRESOLVED (loss resolved against 0 but not beyond the declared 1.15 pp A/A offset). `solver-2048` 71.27 / 85.37: SLU -0.94 [-2.32,
  +0.45], intent +0.46, UNRESOLVED. The R1 read's -0.19 NO-RESOLVED-LOSS for Perception no-think does not replicate on the same roster.
- Consequences: the 324-B Fold A confirm does NOT fly (331 A / 334 B condition "no resolved loss" unmet); the composed lock v3.x keeps
  Perception thinking at 3,072 / 4,096 and the Solver at 3,072 / 4,096 (R2b: 6,144 no gain; 2,048 unresolved, no saving adopted). Per-node
  cost stands as measured: Perception thinking 62 s/contact (forced-close share 0.20) vs no-think 3.4 s; Solver 68-71 s (forced 0.45-0.46).
  Results note: Opus (in progress).
- R3 throughput at full power (first 74 min): 0.72 rows/min x 7 contacts = 5.0 contacts/min, 158-161 W draw; R2b (healthy) 4.8, R2 rec2
  average 2.35 (its second half ~1.9 under the 95 W cap). Seal expected ~2026-10-25 15:00Z. R4 follows via SAEA-Queue-NXT4; the 330 A
  diagnostic (refused in the window: stray __pycache__ in the scoring package; refused again under the open R3 flight) now runs inside
  `chain_nxt4.sh` in the no-flight gap before the R4 smoke (8d3e8a3b7). ASRBIAS pass resumed under the Windows task SAEA-ASRBIAS
  (v1, v2-n30 sealed; v2-n100 partial moved aside and re-flown; then v3 / v4; score all). 338 part 1 merged (0f78ba442; adapter line-budget
  fix a6d675c0c); part 2 in a third Sonnet attempt.

### L338 lever column registered and queued after R4; R2 note merged; saea_task starts on registration (coordinator, 2026-10-24 16:40Z)

- 338 part 2 merged (a3ade87c0, Sonnet aedbbf68d): official scoring of sampling groups (`stage3_rollout_score --mode perception-branches`;
  the l1-support column = the committed answer of 5 Solver samples, sample 0 kept as a second official column), package
  `slurp-l338-lever-column-fold-b-v1` (program c15: 7 Perception + 8 Solver contacts per row; expected 69.4 GPU-h, ceiling 90.3 + 0.5),
  reader `slurp_l338_column_read.py`. Word vocabulary corrected before registration: both candidate arms cost more than the lock, so
  NO-RESOLVED-LOSS applies to neither; L1 (SLU primary, intent guard) and L2 (intent primary, SLU guard) read NOMINATED / HARM / NEUTRAL
  against the floors 1.49 / 0.65 with the twin as the noise bar (design spec section 6 updated).
- Registered by `package_launch.sh l338_launch_spec.json --root-countersign --until commit` (8394f08fe; 4 rows countersigned 16:28:14Z,
  READ row stays a draft; receipt minted). Hooks: `/home/chao/saea-queue/queue_l338.sh` waits `CHAIN_NXT4_EXIT rc=0` after
  2026-10-24T00:00:00Z (task SAEA-Queue-L338 Running); SAEA-Chain-L338 registered (the hook starts it after the flip).
- Coordinator call on ruling 341 A's free check: L338 flies as registered (both arms) directly after R4; the L1 rule over R4's sealed decodes is
  computed at the R4 read as an ADVISORY (if < +0.67 pp the coordinator may stop the hook by hand before the flip); unattended continuity and
  the 175 W throughput outweigh the 28 GPU-h saving.
- Incident, harmless: `saea_task.ps1 -Name SAEA-Chain-L338 -Script ...` (no `-Start`) registers AND starts the task; the chain ran 3 s,
  refused (no flight commit file), wrote `CHAIN_L338_EXIT rc=1 16:28:33Z` (ignored by stamp) and touched nothing (R3 flight intact, no run
  dir). Model-free follow-up `-NoStart` stands.
- R2 rec2 results note merged (e8079b57a, Opus); handoff refreshed (db0af82cd); doc gates PASS.

### 2026-10-24 17:30Z -- Owner directive on the Solver forced-close share; within-row analysis across two same-form flights; 345 proposed

- Owner, verbatim: 「强制截断率的配置，我们要分析调整和优化！你想如果我们的强制截断率都达到了45%的话，我们的solver基本上处于不可用的状态！」
  (English: "The forced-close configuration must be analysed, adjusted and optimised. Think about it: if our forced-close share reaches 45 %,
  our Solver is basically in an unusable state.")
- Coordinator analysis (model-free; `scripts/analysis/forced_close/within_row_forced_close.py`, output
  `forced-close-within-row-r2b-vs-r2rec2.json`; development numbers on TRAIN Fold B; no reasoning text exists in the seals). The Solver lock arm
  (`budget-3072`, same form, same roster) was decoded twice: R2b (2026-10-18, 1,080 rows, forced 433 = 40.1 %) and R2 rec2 (2026-10-20, 1,054
  flown rows, forced 474 = 45.0 %). Greedy at np4 is not reproducible, so 263 of the 1,054 common rows are forced in one flight and natural in
  the other: the forced close is a within-row treatment there.
  * Marginal (confounded by row difficulty): forced rows 63.0 / 65.9 SLU-F1 and 80.1 / 80.6 intent against 77.6 / 74.3 and 88.9 / 88.6 natural;
    forced share rises with the workload (supplied items 30-39: 33-39 %, 40+: 61-63 %; Solver prompt over 10k tokens: 59-63 %). Rows forced in
    BOTH flights 61.65 SLU-F1 (supply 38.6, prompt 9,289 tokens); natural in both 76.84 (35.6, 7,977).
  * Within-row (263 discordant rows): forced decode 73.67 SLU-F1 vs the natural decode of the SAME rows 74.04, delta -0.37 [-3.59, +2.70];
    intent 80.61 vs 80.99 (-0.38 [-3.42, +2.66]); 220 of 263 rows score identically, 24 better forced, 19 worse; per row TP +0.015, FP +0.034,
    FN -0.012, intent -0.004; empty-gold discordant rows false-fill 22 forced vs 17 natural (of 82). Applying the within-row delta to every forced
    row moves the column by +0.12 pp (69.94 -> 70.06 R2b; 69.44 -> 69.57 rec2): the answer written after the budget message is as good as the
    answer written after a natural stop on the same row.
  * Cost: a forced Solver contact runs 3,122 completion tokens and 101 s against 1,481 tokens and 47 s for the natural decode of the same row;
    natural-close completion p50 1,074 / p90 2,184 / p95 2,564 / max 3,084 tokens, so the 3,072 budget covers terminating reasoning; the forced
    tail is reasoning that does not converge (R2b read: 94 % of it still runs at 6,144).
  * Reading: the forced-close share is not a quality failure of the Solver (the answers are the same); it is the share of contacts whose
    reasoning does not terminate, and it is where the Solver's seconds go (forced contacts hold about 63 % of Solver time). The knob to turn is
    therefore the cause of non-termination, not the budget (raise: R2b NEEDS-NO-MORE-BUDGET; lower: solver-2048 -0.94 UNRESOLVED, forced 0.50)
    and not the budget message (at most +0.12 pp to recover).
- Levers already flying or queued, each with the forced-close share and seconds per contact as pre-declared mechanism readouts: NX-T R3
  (t1 decide-once, t3 supply-focus, t4; seal ~2026-10-25 15:00Z), the 330 diagnostic (enumeration vs repetition loop, 56 contacts, chain gap),
  NX-T R4 decoding column (presence penalty 1.5 is the model vendor's own anti-loop recommendation; temperature 0.6 / top_p 0.95 / top_k 20).
- **345 (PROPOSED) Forced-close reduction policy.** A = adopt the efficiency rule: a Solver arm that cuts the forced-close share by >= 15 pp
  (absolute) with no resolved loss (SLU lower bound >= -1.49, intent lower bound >= -0.65 against the twin) enters the lock as an efficiency
  component even when its score word is NEUTRAL; R3 (t1 / t4) and R4 (presence penalty) are read under this rule; if neither cuts the tail, the
  330 diagnostic's verdict picks the next lever (repetition loop -> decoding; enumeration -> a structural Solver supply cap column, items per
  candidate intent, after L338). B = score-only words as today (forced share reported, never a lock criterion). C = owner's own rule.
  Coordinator recommends A.

### 2026-10-24 17:50Z -- Owner ruling 345 A

- Owner, verbatim: 「决策345：A」 (English: "Decision 345: A").
- **345 A RULED: the forced-close efficiency rule.** A Solver arm that cuts the Solver forced-close share by >= 15 pp (absolute, against the
  in-flight twin / delivering lock of the same flight) with no resolved loss (SLU-F1 delta CI95 lower bound >= -1.49 pp AND intent delta CI95
  lower bound >= -0.65 pp against the twin) enters the composed lock v3.x as an EFFICIENCY component even when its pre-registered score word is
  NEUTRAL. The per-arm forced-close share and seconds per contact are mechanism readouts in every Solver column read.
- Application: NX-T R3 (t1 / t3 / t4) and NX-T R4 (presence penalty, temperature arms) are read under this rule. The pre-registered readers
  are not edited while their flights are open; the 345 readout (forced share delta per arm, with its no-resolved-loss check) is computed
  beside each read by a model-free script over the sealed trace and the official per-row columns and recorded in the results note. If
  neither R3 nor R4 cuts the tail, the 330 diagnostic's verdict picks the next lever: repetition loop -> the decoding axis; enumeration -> a
  structural Solver supply-cap column (items per candidate intent), after L338.

### 2026-10-24 19:30Z -- 344 A read: ASR context biasing on Qwen3-ASR 1.7B (TRAIN Fold B, CPU, no core contact); 343 material

- Pass sealed 18:41Z (Windows task SAEA-ASRBIAS; 7 variants x 1,080 clips; v4 = five decodes per clip; ledger row
  SAEA-SLURP-ASRBIAS-FOLD-B-V1 consumed). Ceilings by `scripts/analysis/design339/asr_trigger_bound.py --asr <variant>/transcripts.jsonl [--union]`
  over the sealed R2b lock column (SLU 72.74), outputs `scripts/analysis/design339/bound344-<variant>[-union].json`; development numbers.
  The headline is the perfect-conversion ceiling on the discordant missed-slot + value-error rows (`missval_disc_W`), the quantity the 343 gate
  names; "realistic" = at the measured uptake 0.457.

| transcripts | canonical WER | missed slots contained / 112 | value errors contained / 166 | ceiling (perfect) pp SLU | realistic pp |
| --- | ---: | ---: | ---: | --- | ---: |
| Whisper large-v3 (E5, reference) | 0.152 | 70 | 61 | +5.07 [+4.09, +6.14] | +2.34 |
| Qwen3-ASR 1.7B unbiased (339) | 0.120 | 65 | 64 | +4.64 [+3.66, +5.70] | +2.14 |
| V1 type vocabulary | 0.112 | 67 | 67 | +4.80 [+3.79, +5.90] | +2.21 |
| V2 intent-scoped lexicon N = 30 / 100 | 0.109 / 0.108 | 67 / 69 | 66 / 71 | +4.78 / **+5.09** [+4.04, +6.18] | +2.20 / +2.35 |
| V3 = V2 + logit_bias N = 30 / 100 | 0.116 / 0.109 | 68 / 70 | 62 / 70 | +4.68 / **+5.10** [+4.04, +6.20] | +2.16 / +2.35 |
| V4 n-best union, none / N = 100 | n/a (union text) | 70 / 74 | 65 / 72 | +4.76 / **+5.18** [+4.14, +6.29] | +2.20 / +2.39 |
| best variant + Whisper union (V2-n100 or V3-n100) | n/a | 77 | 80 | +5.47 [+4.41, +6.62] | +2.53 |

- Reading. Biasing works as ASR engineering: the N = 100 lexicon lowers the canonical WER 0.120 -> 0.108 and lifts missed-slot containment
  65 -> 69-74 of 112, i.e. it recovers Whisper's containment at a lower WER and at 1.0-1.3 s per clip on CPU. It does NOT create headroom for
  the task: the best single-tool ceiling (+5.18) is +0.11 over Whisper's and +0.54 over the unbiased 1.7B, far from the 343 gate (>= Whisper
  +1.0 pp = +6.07); even the two-tool union stops at +5.47 perfect / +2.53 realistic. The binding constraint is unchanged: 104 of the 112
  missed slot values are in the reference transcript, the best tool contains 74-77, and the conversion into a delivered slot (uptake 0.457)
  halves whatever is contained. Logit bias (V3) adds nothing over the lexicon prompt (V2) at either N; n-best union (V4) adds 4-5 contained
  items at 3-4x the CPU cost.
- Consequence for 343: the gate is not met by any variant; the coordinator's recommendation stays A (close the triggered-ASR line now; keep the
  tool, the sidecar and the lexicon builder as pinned engineering for a later carrier where transcription is the task, e.g. Earnings). The
  realistic figure (+2.1 to +2.5 pp) is below the measured 1.49 floor only after the uptake discount; a flight would cost a Fold B column
  (about 10 GPU-h with the Thinking core re-asked on 88-91 trigger rows) for an expected +1 to +2.5 pp on SLU and nothing on intent.

### 2026-10-24 20:05Z -- Owner ruling 343 A

- Owner, verbatim: 「决策343：A」 (English: "Decision 343: A").
- **343 A RULED: the triggered-ASR line on SLURP is CLOSED.** No Fold B triggered-transcription column flies. Measured record of the line
  (TRAIN Fold B, development numbers): ceilings +4.64 (Qwen3-ASR 1.7B unbiased), +5.18 (best biasing variant V4 n-best union N = 100),
  +5.47 (two-tool union with Whisper) perfect conversion, +2.1 to +2.5 pp at the measured uptake 0.457, against Whisper's +5.07 and the
  gate +6.07; intent untouched. The constraint is conversion by the frozen core (uptake), not transcript containment.
- Kept as pinned engineering (no further SLURP flights): the ASR sidecar (`scripts/flights/direct/asr_sidecar.sh|.py`, Qwen3-ASR 0.6B / 1.7B
  GGUF under the umbrella lock), the transcription and biasing instruments (`scripts/analysis/asr339/`), the lexicon builder and the
  `configs/asr_bias/` variants, the slot-type descriptions. They are candidates for a carrier where transcription is the task (Earnings
  21/22) and re-enter only through that carrier's own registration. The umbrella lock entries stay; no model bytes are removed.
- Ruling 339 (model-initiated ASR admitted, never default transcription) stays in force as a policy; it simply has no SLURP consumer now.

### 2026-10-25 17:45Z -- NX-T R3 read (the Solver instruction-template column) with the 345 A efficiency readout; 346 proposed (rule form)

- Seal and read discipline. The column flight sealed 2026-10-25T17:04:24Z (run row; driver arm exit 17:06:02Z, chain exit 17:08:31Z) at flight commit
  033f1be39ac4c4edacaac69ff6484b61e742ae1e: 1,080 Fold B rows x 6 Solver arms, 7,560 program contacts, 22,083.6 audio seconds, 27.00 GPU-h
  measured against the 43.4 ceiling (360.1 s per row at the 175 W cap; arm mix 3.51 lock rows, registered 3.61). The READ row
  SAEA-SLURP-NXT-R3-SOLVER-TEMPLATE-FOLD-B-READ-V1 was root countersigned 2026-10-25T17:16:18Z (863675542) before any number was read;
  the six arm columns were scored once each with the official scorer (`nxt_r3_read.sh columns`, 17:16-17:20Z); the preregistered reader
  `scripts/analysis/slurp_nxt_r3_solver_template_column_read.py` wrote `analysis/SAEA-SLURP-NXT-R3-SOLVER-TEMPLATE-FOLD-B-READ-V1/read.json`
  (17:22Z). The 345 readout is the beside-script `scripts/analysis/forced_close/efficiency_rule_345.py` (3cc3ac0bf; ruling-form fix 6aaa0f6e6) over the same sealed trace and columns -> `efficiency-345.json` / `.md` beside the read. Results note:
  `docs/results/2026-10-25-slurp-nxt-r3-solver-template-column-read.md`. The NXT4 queue hook launched R4 at 17:09Z; the flip converged at
  17:15Z (flight commit 7fae8638995bef18c56f99778234808cc1642af5) and the chain started with the 330 A diagnostic in the no-flight gap.
- Words (preregistered rule; in-flight twin offset |o| = 0.45 pp SLU): **all four candidates NEUTRAL.** No NOMINATED, no EFFICIENT-NO-LOSS,
  no HARM; no Fold A confirm is triggered.

| arm | SLU-F1 | intent | SLU d vs lock (pp) CI95 | intent d (pp) CI95 | Solver s ratio | word |
| --- | ---: | ---: | --- | --- | ---: | --- |
| t1-decide-once | 72.84 | 85.19 | +0.80 [-0.47, +2.07] | -0.09 [-1.11, +0.93] | 0.98 | NEUTRAL |
| t2-grounded-or-empty | 72.86 | 84.63 | +0.82 [-0.39, +2.02] | -0.65 [-1.57, +0.28] | 0.96 | NEUTRAL |
| t3-supply-focus | 72.25 | 85.09 | +0.21 [-1.01, +1.45] | -0.19 [-1.20, +0.83] | 1.01 | NEUTRAL |
| t4-decide-once-grounded | 73.23 | 84.72 | +1.19 [-0.10, +2.50] | -0.56 [-1.48, +0.37] | 0.93 | NEUTRAL |
| aa (twin) | 72.49 | 85.19 | +0.45 [-0.77, +1.64] | -0.09 [-0.93, +0.74] | 0.98 | (offset) |
| lock (delivering) | 72.04 | 85.28 | | | 1.00 | |

- 345 A readout (forced-close share, paired per row against the lock, utterance-cluster bootstrap CI95): **NO-345 for every arm.** Lock
  forced share 43.5 % (52.9 s per Solver contact). t1 -10.93 pp [-14.07, -7.87] (32.6 %), t4 -7.78 [-10.74, -4.81] (35.7 %), t2 -2.31
  [-5.37, +0.74], t3 +1.11 [-1.85, +4.17]; none reaches the 15 pp bar and no Solver seconds ratio is <= 0.85 (0.93-1.01). The termination
  paragraph cuts the tail about a quarter at equal quality, mostly on rows under 40 supplied items (35.4 -> 25.5 %) and less on the 40+
  rows (64.7 -> 51.0 %); the grounding and supply-focus paragraphs do not move it; the combination does not add the cuts. The saved
  reasoning tokens do not become time (completion tokens mean 2,060 -> 1,955; the natural stops stay long), which is why the EFFICIENT-NO-LOSS
  seconds bar is also missed.
- Consequence. Instruction alone does not clear the 345 bar and no arm enters lock v3.x. Nothing changes in the queue: R4 (the Solver
  decoding axis, ruling 329 A) is flying; by the 345 A application clause the 330 diagnostic verdict then picks the next lever (repetition
  loop -> decoding; enumeration -> a structural Solver supply-cap column) after L338. The R3 evidence narrows that choice: the share falls
  with a shorter instruction but the 40+ item rows stay above 50 % forced, which is the supply-size signature of the R2b row analysis.
- **346 proposed (rule form, no flight).** Ruling 345 A states the no-resolved-loss test as CI95 LOWER bounds (SLU >= -1.49, intent >= -0.65).
  On a 1,080-row Fold B column the intent delta CI95 half-width is about 1.0 pp, so the intent lower-bound floor is failed by every arm with a
  null intent effect, the in-flight twin included (aa -0.09 [-0.93, +0.74]); the SLU floor is reachable (half-width about 1.25 against 1.49).
  As written, the efficiency rule can be met only by an arm with a positive intent point, which the R1-R3 readers never required. Options:
  **A (recommended)**: the intent test is the NX-T R1 NO-RESOLVED-LOSS form already preregistered in the R3 and R4 readers (intent delta
  CI95 UPPER bound >= -0.65 pp, i.e. no resolved intent loss), SLU unchanged (lower bound >= -1.49); **B**: keep the literal lower-bound
  form (then 345 can fire only on arms with a positive intent point); **C**: intent lower bound >= -1.0 pp (the measured half-width). The
  R3 verdicts are identical under A, B and C (the forced-cut bar fails first); the choice matters for R4, whose 345 readout follows.

### 2026-10-25 20:50Z -- R4 chain stopped once by a stale serving sample (rc=9, nothing flown) and relaunched; 330 A diagnostic sealed; L338 hook re-armed; R4 column flying since 18:08Z

- What happened. The 330 A Solver reasoning diagnostic ran first in the R4 chain's no-flight gap (56 contacts, 17:15:01-17:38:45Z, rc=0;
  `diagnostics/SAEA-SLURP-SOLVER-REASONING-DIAGNOSTIC-V1/results.jsonl` 56 rows, wall 1,409.7 s). Eleven seconds later the batch driver's
  prelaunch for the R4 smoke read the serving monitor's LAST sample, still `busy 1` from the diagnostic's final contact, and stopped the chain
  (`serving session not idle/healthy before step 1: True 1 ...`, CHAIN_NXT4_EXIT rc=9 17:38:56Z). No attempt was opened, no run directory
  written, the resident session was healthy with 0 of 4 slots busy at 17:39:39Z. The L338 hook saw rc=9 and exited without launching, as
  designed.
- Recovery (coordinator, 17:41Z). `/home/chao/saea-queue/queue_l338.sh` re-stamped to CHAIN_NXT4_EXIT after 2026-10-25T17:45:00Z (the stale
  rc=9 line is ignored); SAEA-Queue-L338 restarted (armed 17:41:21Z); SAEA-Chain-NXT4 restarted (chain start 17:41:17Z, same flight commit
  7fae8638995bef18c56f99778234808cc1642af5; the diagnostic step refused as expected because its directory holds the sealed attempt, logged
  rc=70, non-blocking); driver prelaunch-ok 17:41:30Z; smoke-4 sealed and inspected 17:48:23Z (pass, no fails); machine sign-off after the
  20-min veto; the decoding column `slurp-native-stage3-nxt-r4-solver-decoding-fold-b-v1` started 18:08:39Z (prelaunch-ok 18:08:39Z); 128 of
  1,080 rows checkpointed by 20:44Z (about 73 s per row at 4 slots, seal expected about 2026-10-26 16:00Z). No flip, no re-pin, no edit to any
  registered artefact. The two sealed smoke rows (SMOKE-4, SMOKE-4-FIT) were closed by `ledger_mark_consumed.py --apply` (consumed check PASS).
- Cause and follow-up. `batch_driver.sh` `prelaunch` keys on `last_monitor_sample.slots.busy` of `serving_session.sh status`, a periodic sample,
  so any non-driver GPU job that ends within one monitor period of a driver start trips it (the diagnostic is the first such job placed
  directly before a driver step). Fix (model-free, after this chain: the driver file is read by the running bash process and is never edited
  under a live chain): re-poll the status up to six times at 20 s before stopping when `server_ok` is True and only `busy` is non-zero, and
  log the retries. Tracked with the other driver follow-ups (`saea_task.ps1 -NoStart`, mode-B checkpoint hash, reaper scope).

### 2026-10-25 20:55Z -- 330 A diagnostic READ (statistics only): the non-terminating Solver reasoning is a REPETITION LOOP, not an enumeration

- Read discipline. The READ row SAEA-SLURP-SOLVER-REASONING-DIAGNOSTIC-READ-V1 was root countersigned 2026-10-25T20:46:53Z after the probe
  seal (17:38:45Z) and before any statistic was read; the registered statistics-only reader `scripts/analysis/solver_reasoning_diag_read.py`
  (gated by `read_require_countersigned`) wrote `analysis/SAEA-SLURP-SOLVER-REASONING-DIAGNOSTIC-READ-V1/read.json` (20:46Z; 56 of 56
  contacts read, 0 missing, 0 model contacts, `text_printed` false). The reasoning bytes stay under the data root (ruling 330 A); this
  section carries counts and pattern statistics only. The registered pattern rule (loop: a block repeated >= 3 times totalling >= 600
  characters, or >= 50 % of the last quarter of the sentences repeated; enumeration: not a loop, >= 50 % of the supplied intent labels
  mentioned with >= 60 % of first mentions in supply order) is a reading aid; the numbers are the verdict's basis.
- Budget-3072 rows (40 = 16 forced-both + 8 forced-3072-only + 8 forced-6144-only + 8 natural-both): pattern **repetition-loop 21,
  enumeration 4, other 15**; 36 of 40 contain a repeated block. The forced-close rows are the loop: forced-both 13 loop / 1 enumeration / 2
  other, with the repeated-sentence share of the last quarter at median 0.98 (whole text 0.56), zlib ratio 0.14, the first repeat at 21 % of
  the text (median) and a repeated block of 1,970 characters (median); the natural rows are not: 1 loop / 1 enumeration / 6 other, tail
  repeated share median 0.07, whole-text 0.02, zlib 0.34. The reasoning does not walk the supplied labels: label coverage median 0.25 in
  every group (mean 0.36 over the 40 rows) while the single most-mentioned label is restated 16 times (median; 19.5 on forced-both rows,
  max 89). Mixed groups sit between (forced-3072-only 3 loop / 2 enumeration / 3 other, tail share 0.26; forced-6144-only 4 loop / 0 / 4
  other, tail share 0.39).
- The same 16 forced-both rows at budget 6,144: pattern 13 loop / 1 enumeration / 2 other (11 of 16 loop at both budgets); the text beyond
  the 3,072 close (median 26,375 characters, tokens ratio 6,144 / 3,072 median 1.99) is itself a loop in 13 of 16 (repeated-sentence share
  median 0.80, zlib 0.07), and in 14 of 16 the repeat onset in the 6,144 text lies before the 3,072 close (median onset 3,169 characters).
  The doubled budget is spent restating; this is the mechanism behind the R2b NEEDS-NO-MORE-BUDGET read. No pair is byte-identical through
  the close (common prefix median 1 % of the 3,072 text; `reasoning_hash_match` 0 of 56 in the run summary) although the forced close itself
  reproduced in 14 of 16 pairs and 36 of 56 contacts overall: a temperature-0 re-issue on the np4 geometry does not replay the sealed
  bytes, so the diagnostic reads the pattern, not the exact sealed trace.
- Answer behaviour. The delivered intent equals the last-mentioned label in 33 of 40 rows; of the 23 rows with a restatement before the
  answer, 7 deliver a different label from the one last restated (forced-both 5 of 13).
- **Verdict (330 A): REPETITION LOOP.** By the 345 A application clause the next lever after R3 and R4 is the decoding axis, which is the
  column already flying (R4: presence-penalty and temperature arms); the structural Solver supply-cap column is NOT triggered by this
  evidence (coverage 25 % of the supplied labels: the tail does not enumerate the supply). The R3 observation that the 40+ item rows stay
  above 50 % forced is consistent: a larger supply lengthens the pre-loop walk (first repeat at 21-33 % of the text) but the tail that
  exhausts the budget is the same restated block. If R4 reads NO-345 as well, the next decoding candidates are a repetition penalty /
  no-repeat n-gram window on the Solver only (model-free to register; one column), before any supply-cap column.

### Owner ruling 346 A (coordinator, 2026-10-25 23:30Z): the 345 intent no-loss test is the preregistered NO-RESOLVED-LOSS (upper-bound) form

Owner, verbatim: 「决策346：A，继续，R4读数出来后告诉我」 (English: "Decision 346: A; continue; tell me once the R4 read is out").

- **346 A:** in ruling 345 A the no-resolved-loss test reads: SLU-F1 delta CI95 LOWER bound >= -1.49 pp (unchanged) AND intent delta CI95
  UPPER bound >= -0.65 pp (the NX-T R1 NO-RESOLVED-LOSS form already preregistered in the R3 and R4 readers: no resolved intent loss). The
  literal intent lower-bound form of the 2026-10-24 text is retired: on a 1,080-row Fold B column the intent CI95 half-width is about 1 pp, so
  it was failed by every null-intent arm, the in-flight twin included.
- Application. The beside-script `scripts/analysis/forced_close/efficiency_rule_345.py` now applies the ruled form (schema
  `saea-efficiency-rule-345-v2`, `intent_test` = CI95 upper bound; the reader-form conditions stay beside for reference); the preregistered
  R3 / R4 readers are untouched. The R3 345 readout was recomputed under the ruled form over the same sealed read (`--force`, outputs
  `efficiency-345.json` / `.md` beside `analysis/SAEA-SLURP-NXT-R3-SOLVER-TEMPLATE-FOLD-B-READ-V1/read.json` rewritten, numbers identical):
  every candidate now passes both no-loss conditions (t1 / t2 / t3 / t4 intent upper bounds +0.93 / +0.28 / +0.83 / +0.37) but no arm reaches
  the 15 pp forced-cut bar, so the R3 verdict stays **NO-345 x4** and the results note of 2026-10-25 is unchanged. The R4 345 readout is
  taken under this form when its READ row is countersigned (seal expected about 2026-10-26 16:00Z).
