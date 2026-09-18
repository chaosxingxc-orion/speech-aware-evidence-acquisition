# SLURP next stage: owner decisions of 2026-09-16

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
("你不要重新开始跑吧，看下是否可以断点续推？"). The harness had no resume capability.

| # | Question | Decision |
| --- | --- | --- |
| 22 | May a flight that died of an infrastructure failure be completed by a resume-recovery instead of a full re-fly, and what is the rule? | Agreed ("决策22同意"). A resume-recovery is a recovery re-registration (one per flight, root-diagnosed) that applies ONLY when code and request bytes are unchanged (infrastructure failure, never a harness or config defect): every complete row of the aborted attempt is kept without selection, every partial or unstarted row is flown by the recovery attempt under the same run id, the merged manifest declares the predecessor attempt (trace hash, kept-row list and its hash) and scores once; the bundle verifies kept rows against the predecessor trace byte for byte. Item E10 builds it; the B4b replicate is its first use. **Standing rule (owner, same message): every experiment registered from now on must support checkpoint resume** ("我们后期所有的实验都要支持断点续推的能力"); the fixed protocol and every new preregistration's failure rule carry the resume-recovery clause. |

## Owner decisions 23-24 of 2026-09-18 (after cell B5e was registered and before any B5e number was read)

| # | Question | Decision |
| --- | --- | --- |
| 23 | The B5e preregistration's bar clause reads the v3-projected numbers (decision 7); the additive arithmetic clears 64 only in v3 terms (62.67 + 2.06 = 64.73) and not in official terms (61.14 + 2.55 = 63.69). Which metric is the bar, and may gains be summed? | Owner (translated): "Such gains cannot be added mechanically; is it confirmed that the combined gain is obtainable by addition? Our final evaluation must still be based on the official evaluation, aligned with the community's standard scheme." Consequences: (a) gains are never assumed additive; a combination is read from its own measured score, and additivity is reported only as a diagnostic; (b) **the program bar and every final evaluation read the OFFICIAL, unprojected SLURP `evaluate.py` number** (pooled SLU-F1 >= 64.00 and intent >= 78.00 on `slurp-slu-official-train`), the community-standard protocol; projection v3 stays a fixed diagnostic reported beside every official number (this revises the reading of decision 7: v3 is no longer the number the bar reads). Recorded before any B5e number was read; the B5e bar clause is amended by `docs/readiness/2026-09-18-slurp-b5e-combination-v1-amendment-decision-23.md` without touching the sealed preregistration bytes. Implication stated to the owner: B5e will most likely miss the official bar by a few tenths, and decision 20 (keep admitting, read B5b) applies. |
| 24 | Machine power and process ownership after three infrastructure deaths in one day (ChatGPT session closed at 02:40Z; laptop shut down at 03:36Z; the coordinator's own `powercfg` change tripping the scheduled tasks' stop-on-battery condition at 14:40Z). | Owner: "adjust it yourself; I will not shut down; but also compare comprehensively the modes that can support resume." Consequences: AC sleep and hibernate set to never (done 14:40Z); the serving wrapper, the monitor and every campaign run as Windows Scheduled Tasks registered with the battery and idle conditions disabled and no execution time limit, so they survive Claude Code restarts; the coordinator never changes power settings while tasks run; item E10 documents a comparison of resume modes (trace replay and seal-time merge, incremental row checkpoints, chunked sub-attempts) with the trade-offs and the chosen mode. |

Outcome of decision 18 (2026-09-18, after the twin read): branch A. (B1 minus twin) reads +7.83 pp official pooled SLU with a CI95 of [+5.85, +9.75]; cell B1 is ADMITTED and module M1 is admitted as speech-keyed exemplar supply. The twin alone reads +4.77 pp [+3.20, +6.36] over the anchor with nil intent, recorded as a decomposition fact; module M1p is not registered. Record: `docs/results/2026-09-18-slurp-b1-twin-verdict.md`. Cell B5e therefore combines M1 (the arm's form) with M4b.

