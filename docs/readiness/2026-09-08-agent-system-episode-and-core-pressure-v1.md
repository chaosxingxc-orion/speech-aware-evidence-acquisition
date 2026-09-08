# The agent system: four agents in one loop, and the core-pressure covariates (design note, 2026-09-08, revision 2)

**Status: DESIGN NOTE, model-free, no cell registered.** It restates how every Stage-2 cell from here on is
specified, after the owner's correction of 2026-09-08. Nothing in it changes a sealed result, a comparator or a
rule already preregistered; it changes what the next preregistrations must say.

## 1. The correction, and the evidence that agrees with it

The owner's words, in substance: the recent cells transferred the whole task load onto single calls of the
frozen core; the object of the study is an agent *system* whose system-level optimization lowers the core's
burden and raises task performance systematically; and a ReAct-style revise stage that evaluates the quality
of an answer and proposes revisions should be considered.

The sealed record agrees with the correction, cell for cell:

| cell | how the load was split | result |
|---|---|---|
| KC-E1 (2026-09-07) | the whole ConEC brief in one prompt, one call per window, the core asked to transcribe and to use the brief at once | primary met (PERSON +4.15 pp) but HARMFUL: deletions +2,692, corpus WER +0.54 |
| KC-E1f (2026-09-08) | the system supplied the sealed draft, constrained the edit to span-bounded substitutions, and asked the core only to fix names | primary met (PERSON +3.74 pp), corpus WER better, deletions unchanged; rejected only by margin-less guard wording |
| KC-S1b (2026-09-05) | the system sealed the intent first and asked the core to fill slots from a schema of that intent | ADMITTED, SLU-F1 +10.1 |
| KU-S1 / MF-7b (2026-09-06) | an external embedder was asked to do the matching for the core | closed: about zero net corrective power |

The pattern: gains appear when the *system* narrows the problem and constrains the edit, and losses appear when the
core is handed the open problem plus more context.

## 2. Revision 2 (same day): four agents in one loop, with a planner

The owner's second correction: the first draft of this note read as a pipeline of many functions; the system
must converge to a FEW named agents calling each other in a loop, with a planning mode, and with observation
modes chosen per task (a meeting task calls speaker diarization; a noisy input calls enhancement; the loop
listens selectively to the key audio worth improving). The seven-step table of the first draft is therefore
folded into four agents. Knowledge is not an agent: it is the store the agents consult (the three dimensions:
text-domain knowledge, same-speaker speech exemplars, state).

| agent | performer | responsibility | today's seam |
|---|---|---|---|
| **Planner** | system | from the task type and the state, picks the observe mode(s), the knowledge views to supply, the budget of core calls, and when to stop; a rule table now, the object the evolution loop optimizes in Stage 3 | phase programs and their config; `LoopConfig` |
| **Observer** | system + pinned tools | executes the observe mode: input standardization (rate, tail), unit choice (speaker-turn units via diarization for meetings; fixed windows otherwise), enhancement when the input is noisy, and SELECTIVE LISTENING: re-listening only to spans the Reviewer flagged, with more context | `reproduction.obs_loop` (unit plan, tail knob), the Sortformer diarization tool row, the replay loop's flagged spans |
| **Solver** | the frozen core | the only answering agent: a draft, then constrained revisions, always on the narrowed problem with the supplied knowledge | `EvidenceAgentController` phases, `window_hook`, the post-processors |
| **Reviewer** | system judges (deterministic checks, pinned frozen tools; later the core in a critic phase that flags but never answers) | scores the draft against knowledge and state, flags spans, and returns the decision to the Planner: loop (acquire, re-listen, revise) or commit | registered scorers and post-processors in `core.base`; `e21-entity-repair-substitutions-v1`; the legal-label projection |

The loop: **Plan -> Observe -> Solve -> Review -> (Plan again with the flags, within budget) -> Commit.**
Every carrier runs the same loop; what differs per carrier lives in three mode tables, never in a new pipeline
(one base, thin adapters):

| mode table | entries today | entries named, not built |
|---|---|---|
| observe modes | fixed 90-s windows; speaker-turn units (diarization); silence tail; 16 kHz standardization; ESB clips through the slice path | enhancement for noisy input (a pinned frozen enhancer with a derivation record, testbed = the Audio2Tool noisy tier); selective re-listen of flagged spans with context |
| knowledge views | class lists / brief; TRAIN slot schema per intent; KB facets; slot fillers; the derived-candidates bank | same-speaker exemplar index (MF-8); device inventory and legal-intent state; speaker roles from diarization + brief |
| judges | legal-label projection; schema conformance; substitution-only delivery rule; numeric-format checks | brief-name near-miss detector; decode-confidence signals from the sealed trace; acoustic re-check through a pinned embedder; the core-as-critic phase (after owner confirmation) |

Read against the sealed record: KC-E1f is this loop with the Reviewer and the selective re-listen switched off
(Plan fixed, Observe = fixed windows, Solve = sealed draft then constrained revise). KC-S1b is a two-stage Solve.
OBS-E1 is an observe mode. The E22 encoding fix and the tails are observe-mode standardization. The first cell
that runs the WHOLE loop is the Earnings-21 cell after KC-E1f (section 5).

Experimental discipline is unchanged: a cell still moves one factor. In loop terms, a factor is one agent's
mode or one mode-table entry, and its twin is the same loop with that entry replaced by its form control
(the Reviewer switched off; other-speaker exemplars; a token-matched placebo view).

## 3. Core-pressure covariates, reported by every verdict

Beside the per-stratum tables and the token covariate, every verdict reports:

- core calls per task unit and per row of the roster;
- core prompt and completion tokens per task unit;
- the system's decision share: the narrowing ratio (candidates offered / candidates possible), the judge's
  interceptions (flags raised, flags that led to a revise), and rejected revisions by reason;
- the share of the final answer that the core produced versus the system delivered unchanged (KC-E1f: 447 of
  1,593 windows delivered the draft untouched; 82 refused).

These are covariates, never decision criteria; the decision rule stays the preregistered primary and its
non-inferiority guards with margins from the carrier's own null (family rule of 2026-09-08).

## 4. The revise stage: admitted under three conditions

1. **New information.** SLURP's greedy null is a 28 % flip rate on identical prompts; the EVO-S1 proposer loop
   stalled on it. A reviser that re-reads its own output carries no signal above that floor. The revise stage
   consumes state, evidence or a tool judgment that the draft did not have.
2. **Constrained edits.** Unconstrained regeneration cost 2,242 non-entity deletions in KC-E1. Revisions are
   span-bounded substitutions, projections onto a legal set, or fills inside a schema; the system refuses the rest
   and delivers the draft.
3. **Answer authority stays in the core.** The boundary admits frozen tool-level judges when pinned and logged
   and forbids a second answering LLM. A judge is therefore (a) a deterministic check, (b) a pinned frozen tool
   (an embedder, a scorer), or (c) the same frozen core in a critic phase that flags and proposes but does not
   answer. Reading (c) is the coordinator's interpretation of the boundary and is submitted to the owner for
   confirmation before any core-as-critic cell is preregistered.

Order of work: deterministic and tool judges first, because their precision and recall can be measured
model-free on sealed outputs (which flagged spans are real errors; which real errors were flagged); the
core-as-critic phase needs a flight and comes after.

## 5. What this changes in the two lines in preparation

**Intent line (KU-S4, SLURP).** The system builds the candidate set from state knowledge (the legal intents of the
scenario, the device inventory) and the speaker-exemplar index; the core chooses among k candidates presented with
same-speaker exemplars; a legality judge commits. MF-8 prices the narrowing (recall@k of the gold intent per
candidate source) before any flight; the oracle-candidate arm measures the core's matching alone, the real-candidate
arm measures the system. Twins: other-speaker exemplars (speaker effect) and text exemplars (modality effect).

**Earnings-21 line (the cell after KC-E1f).** The first whole-loop cell: Plan (meeting task -> diarization units, brief as state), Observe (speaker-turn units), Solve (draft), Review (judges flag spans: numeric-format mismatch, brief-name near-miss, low-confidence decode signals), Observe again (selective re-listen of the flagged spans with context), Solve (constrained revise), Commit. In the first draft's words: the episode adds the two steps KC-E1f skipped: JUDGE flags spans
(numeric-format mismatch, brief-name near-miss, low-confidence decode signals available in the sealed trace) and
ACQUIRE re-listens to the flagged span with the relevant brief entries; REVISE stays substitution-only. The core's
calls concentrate on flagged spans instead of all 1,593 windows; the expected core-pressure reduction is itself a
reported number.

## 6. Preregistration template additions

From this note on, a preregistration carries: the episode table of section 2 for the cell; the core-pressure
covariates of section 3 in its reporting list; the judge inventory it uses with each judge's registry id and its
model-free precision/recall receipt where one exists; and the non-inferiority margins with their source row.
