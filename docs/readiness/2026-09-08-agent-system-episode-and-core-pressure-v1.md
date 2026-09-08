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
| **Reviewer** | system judges (deterministic checks, pinned frozen tools; later the core in a critic phase that flags but never answers) | **CRITICISM ONLY (owner Decision 11-C, 2026-09-08): it SCORES and FLAGS, it never proposes a revision.** It scores the draft against knowledge and state, flags spans and fields, and returns a typed verdict to the Planner, whose loop decision is loop (acquire, re-listen, revise) or commit; the revision itself belongs to the Solver, under the system's constraints | judges registered in `core.base.JUDGES` behind the `Judge` protocol, whose `JudgeVerdict` type structurally cannot carry replacement text (`core.base.assert_criticism_only`); the seam is `rails.phase_review` on `EvidenceAgentController`; the frozen checks behind it are the legal-label projection's legality rule, the slot schema-conformance rule, the numeric-format rule, `e21-entity-repair-substitutions-v1`'s refusal reasons, and the `core.replay_signals` / `core.flag_sources` flag sources |

The loop: **Plan -> Observe -> Solve -> Review -> (Plan again with the flags, within budget) -> Commit.**
Every carrier runs the same loop; what differs per carrier lives in three mode tables, never in a new pipeline
(one base, thin adapters):

| mode table | entries today | entries named, not built |
|---|---|---|
| observe modes | fixed 90-s windows; speaker-turn units (diarization); silence tail; 16 kHz standardization; ESB clips through the slice path | enhancement for noisy input (a pinned frozen enhancer with a derivation record, testbed = the Audio2Tool noisy tier); selective re-listen of flagged spans with context |
| knowledge views | class lists / brief; TRAIN slot schema per intent; KB facets; slot fillers; the derived-candidates bank | same-speaker exemplar index (MF-8); device inventory and legal-intent state; speaker roles from diarization + brief |
| judges | legal-label projection; schema conformance; substitution-only delivery rule; numeric-format checks | brief-name near-miss detector; decode-confidence signals from the sealed trace; acoustic re-check through a pinned embedder; the core-as-critic phase (after owner confirmation) |

**2026-09-08, WAVE W4 (owner Decision 11-B change #6): the three mode tables are FOUR CONFIG TABLES with a
null arm, and a fourth table joins them.** Above, a "mode table" is prose. In config it is now `observe`
(per phase: silence tail, speaker-turn unit plan, selective re-listen with its margin, budget, derivation
kind and flag source), `knowledge_views` (per phase: the `phase_material` entry whose `state_fill` IS the
view, and the `phase_supply` entry that IS the retrieval provider), `judges` (per phase: W1's `phase_review`
entry), and — new, from W3's catalog — `toolkits` (which task-type toolkit row is armed, for which agent
roles). `knowledge_views` and `judges` WRAP the blocks E1/E6/W1 already ship without changing a byte of
them and delegate to their existing loaders; a fragment declares the flat block or the table, never both.
The knowledge table is spelled `knowledge_views`, not `knowledge`, because `knowledge` is already a
top-level object in `configs/experiment/a2t-g3-plain-english-v1.json` and `core.config.compose` refuses a
key two fragments define.

Every table has a **null arm**, and the null arm composes to the SAME config hash as the table being absent
(`core.config.drop_null_arms`; `"observe": null`, `"observe": {}` and no `observe` key are one cell
identity, not three). That is what makes section 8's "module ON versus module OFF in the same harness, one
config key, never a second code path" true rather than aspirational: the OFF arm is a twin of the pre-table
baseline instead of a third cell. Six of the seven modules the implementation assessment tabulated now move
exactly one key, proved by composing both arms and diffing the flattened config
(`tests/unit/test_config_table_module_switches.py`). The seventh, the `obs-repair-loop` window hook, still
has no config key at all and stays outside until the E21 obs path moves onto `FlightRuntime` (assessment
changes #8/#9). Two corrections this wave owes the assessment: the substitution-only repair rule belongs in
`judges` (Decision 11-C splits it — the alignment rule that refuses illegal edits is the judge, the delivery
is a Solver constraint), and the retrieval provider needs NO `PhaseSpec.knowledge: "optional"` relaxation,
because `"supplied"` already means the phase MAY be supplied and one program id already carries both arms.

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

**Owner Decision 11-C, 2026-09-08 (amends condition 3 above).** *The Reviewer is CRITICISM ONLY: it
scores and flags, and it never proposes a revision; revisions belong to the Solver, under the
system's constraints.* This supersedes the reading of condition 3(c) that let a core-as-critic phase
"flag **and propose**" -- a critic phase may flag, score and give reasons, and nothing else. A
judge's whole output is a typed verdict: a score, flags carrying span and field references into the
draft, and reasons. That verdict is consumed by the Planner's loop decision and by the Solver's
constrained revise; no judge may emit replacement text.

The `JUDGES` protocol enforces this **structurally**, not by convention. Every registered judge
returns a `core.base.JudgeVerdict`, and `core.base.assert_criticism_only` -- asserted on that type at
import -- refuses any verdict field that could carry text longer than one reason: a field may hold a
scalar, a tuple of scalars, or a type already proven criticism-only, and every text-bearing field is
capped at `MAX_JUDGE_TEXT_CHARS` (240). A mapping or object field is refused outright, because a
mapping can smuggle a whole rewritten answer under any key. `core.base.JudgeRegistry.register`
additionally refuses an entry that does not declare `criticism_only=True`. So the boundary this note
argued for in prose -- answer authority stays with the frozen core, a judge is not a second
answering LLM -- is now a property of the type, and re-opening it costs an import-time failure
rather than a review comment.

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

## 7. Tools: what the four agents call, and how they are supplied through openJiuwen

The owner's third instruction of the day: analyse the tools -- some task-specific, some general -- that the agent
system calls, abstract them, and supply them uniformly; and design and implement on the openJiuwen framework.

**Principle.** A tool is anything an agent calls that is not the frozen core. The core is the Solver behind the
single-door component (`FrozenCoreASR` wrapping `core.model.FrozenCoreAdapter`; adoption memo 2026-08-08), never a
tool. Every tool is pinned and logged (the charter's frozen tool-level clause); a tool that changes bytes leaves a
derivation record (the tail and the 16 kHz media already do); scorers are evaluation instruments and never run
inside the loop. Knowledge stores (class lists, schemas, KB facets, exemplar indexes, state) are not tools; tools
read and build them.

**General tools (carrier-independent), by the agent that calls them.**

| family | existing in the repo | named, not built |
|---|---|---|
| audio I/O and standardization (Observer) | librosa decode, resampling to 16 kHz, the silence tail, slice cutting and encoding (`obs_audio.encode_slice`), duration and energy margins | -- |
| segmentation (Observer) | Sortformer diarization (pinned tool row), the energy pause detector, the speaker-turn unit planner v2 | -- |
| enhancement (Observer) | none | a pinned local enhancer with a derivation record; testbed = the Audio2Tool noisy tier; candidate survey first |
| selective listening (Observer) | the replay loop's flagged spans and re-cut with context | the re-listen mode wired to the Reviewer's flags |
| embedding and retrieval (Observer/Reviewer, keyed by speech) | local encoders (Omni-Embed-Nemotron, LCO-Embedding-Omni, Qwen3-Embedding, GLAP), sealed-vector retrieval, KB facet and dense-centroid providers | the same-speaker exemplar index (MF-8); openJiuwen `core/retrieval` indexing and reranking may host the index, the query stays speech |
| deterministic judges (Reviewer) | legal-label projection, schema conformance, numeric-format check, substitution-only alignment (`core.repair_alignment`), span surgery, flag sources and replay signals, containment and echo checks | brief-name near-miss detector, decode-confidence signals from the trace, acoustic re-check through a pinned embedder |
| budget and tokenization (Planner) | the live `/tokenize` prompt fit, `rails.context_budget`, `core.evidence_budget` | a per-episode core-call budget enforced by the Planner |
| serving and transport (system service) | the resident session with monitor, the featcache packet sidecar, the flight lock | -- |
| tracing, ledger, receipts (system service) | the trace sink, the exposure ledger, MANIFEST receipts | -- |

**Task tools (carrier-specific).** SLURP: the closed intent list and its legality rule, the TRAIN slot schema per
intent, the slot-filler view, the official scorer (evaluation only). Earnings: the ConEC class lists and the
pre-meeting brief renderer, the participant-roster supplement, the ConEC entity-WER mirror and the Whisper
normalizer (evaluation only), the ESB reference conventions, the boundary-bleed detector. Audio2Tool: the 152-tool
registry and its domain grouping, the call-string parser, the `a2t-toolcall` scorer (evaluation only), the
contrast notes. Meetings (future): speaker roles from diarization plus the brief, the agenda.

**Uniform supply through openJiuwen.** Each tool is registered as a `LocalFunction` (the framework's `Tool` base in
`core/foundation/tool`) in the framework's tool manager, with a manifest the Planner reads: id and pinned hash;
typed inputs and outputs; side effects (bytes changed -> derivation record required); cost class (CPU, GPU,
contacts); the axis it serves (OBS / ORG / SUPPLY / USE); scope (general or carrier); the ledger row type it needs.
Observe modes become toolkits selected per task type, which is the framework's own pattern
(`core/controller/modules/intent_toolkits.py`). The loop stays the workflow graph already proven trace-equivalent
(`reproduction/ojw`: `LoopGroup`, `AdvancedLoopComponent`); tool nodes are added to it; the framework's LLM clients,
MCP and RESTful tools stay uninstantiated (paid API 0, no cloud). Red lines of the adoption memo unchanged: single
door, no `openjiuwen` in `pyproject.toml`, deterministic equivalence of the wrapped tools against direct calls.

**First model-free build (named, not scheduled):** the tool manifest and catalog (`rails/tools.py` mapping to
`LocalFunction`), the first eight wrapped tools (diarization, tail and resample, unit planner, legality
projection, repair alignment, flagged-span detector, speech-keyed retrieval, prompt-fit tokenizer), the Planner's
toolkit table per task type (meeting / command / tool-call), and the equivalence test (wrapped output == direct
output, byte for byte).

## 8. One harness on `rails`, and the module admission gate

The owner's fourth instruction: the harness is standardized on `rails` and reused across tasks -- never one agent
system per task -- and before any large-scale test of the engineering base every module must bring a positive gain
or at least not hurt the locked baseline.

**One harness.** The four agents and the three mode tables live in the bases the 2026-09-03 rules already name:
the Planner in the phase program and its loop condition (`rails.controllers.EvidenceAgentController`), the Observer
in `rails.obs` and the observe-mode entries, the Solver behind `rails.core_client` (the single door), the Reviewer
as judges registered in `core.base` and invoked from the controller's phase after Solve; the knowledge views come
from `rails.knowledge_provider.KnowledgeProvider`. A carrier contributes exactly what the base rules allow: one
`data.carriers` descriptor, one adapter under `rails/adapters/`, one scorer registration and config fragments; a
carrier's plan is a row of the Planner's table (its toolkit of observe modes, views and judges), not a code path.
Where today's flows still live outside the bases (the Earnings-21 obs loop under `reproduction/`, the Audio2Tool
flight scripts, carrier-only orchestration modules), the openJiuwen implementation assessment lists each with its
route into a mode-table entry or an adapter method.

**The admission gate.** Every harness module -- a planner rule, an observe mode, a knowledge view, a judge, a tool --
carries a per-carrier admission receipt before it may enter the default plan:

- the contrast is module ON versus module OFF in the same harness on the same roster (one config key, never a
  second code path), paired with the carrier's cluster structure, n >= 400, cluster bootstrap, CI90;
- the guard is non-inferiority with the margin taken from the carrier's own null (family rule of 2026-09-08);
  a positive gain on the carrier's primary metric is the preferred outcome, "no harm" is the minimum;
- the status is one of ADMITTED (gain), NEUTRAL (no harm, no gain) or HARMFUL; the default plan contains only
  admitted or neutral modules; harmful modules stay in the record as documented negatives and never in a plan;
- modules are admitted one at a time; a combined plan is tested at scale only after every module in it holds a
  receipt; the admission table is a living receipt (`docs/receipts/harness-admission.json`) mirrored as a row on
  the umbrella page.

**2026-09-08, WAVE W4: three of these bullets are now enforced rather than written down.** The receipt is at
schema `saea-harness-admission-v2`: every entry names the config table and the key that switch its module,
and `default_plans` names the plans a module may enter. `scripts/checks/harness_admission_check.py`
(model-free) refuses a switch whose key resolves in no table or whose OFF arm is not that table's null arm,
refuses an ADMITTED or NEUTRAL module that reaches no default plan for its own carrier, and refuses a
HARMFUL module — or one whose provisional obligation is still UNMET — armed in any plan. `default_plans` is
empty today: the one decided module is ADMITTED provisionally with its replication UNMET, and its own
verdict note barred it from the default plan until a second independent pass.

**2026-09-08, ON MERGE: a FIFTH switch class, `run`, and the first default plan.** W4 was written
beside the cross-call dispatcher's admission cell and neither could see the other. Merging them
found the gap: the v2 schema required every entry to name one of the four config tables, and the
dispatcher's one config key is `obs_prefetch_depth` — flat, read by `core.driver.run` and
`reproduction.obs_loop`, per-RUN where the four tables are per-PHASE. The tables are not widened.
`rails.config_tables` gains a fifth switch class instead, `run`, whose keys are a CLOSED allowlist
(`RUN_LEVEL_SWITCH_KEYS`, today `{obs_prefetch_depth}`) and whose null arm is the key absent or the
driver's documented default of 0. Being outside the tables is not free: a `run` entry owes a
`falsifier` — `{"kind": "request-bytes-identical", "receipt": <dir>}` — and the check re-hashes that
receipt's `MANIFEST.sha256` rather than believing the path. That is the whole licence: a module that
moves one byte of the request cannot produce such a falsifier and belongs in a table. The dispatcher
has one (1,593 of 1,593 slices byte-identical, `prompt_tokens_total` 1,935,965 to the digit), so it
is admitted to the class and, being NEUTRAL with no blocking obligation, `default_plans` gains its
first entry: `configs/baseline/e21-buf90-zero-locked-scored4-prefetch1.json` for
`earnings21-original`, which is the sealed comparator's own fragment plus that one key. The KC-E1f
repair stays barred exactly as W4 wrote it. No verdict, number, status or evidence pin moved.

**First entries, from the sealed record (2026-09-08):**

| module | carrier | status | evidence |
|---|---|---|---|
| silence-tail observe mode | Earnings-22 | ADMITTED | test 9.24 under the convention |
| silence-tail observe mode | Earnings-21 | carrier-specific: gain on the WER anchor, HARMFUL on PERSON | `SAEA-E21-FULL44-TAIL2S-V1` |
| legal-label projection judge | SLURP | ADMITTED | projection v2 re-lock, +1.70 intent |
| TRAIN slot schema view + two-stage Solve | SLURP | ADMITTED | KC-S1b, SLU-F1 +10.11 |
| substitution-only repair (Reviewer + constrained Solve) | Earnings-21 | **ADMITTED**, provisional — replication UNMET | KC-E1f, v2 re-decision (`SAEA-E21-KC-E1F-VERDICT-V2`); the guards are no longer pending and the entry is in `docs/receipts/harness-admission.json` |
| whole-prompt brief view | Earnings-21 | HARMFUL | KC-E1 |
| embedder intent retrieval view | SLURP | NEUTRAL at best; excluded | MF-7b |
| speaker-turn-unit observe mode | Earnings-21 | pending | OBS-E1 in the queue |
| cross-call dispatcher (throughput) | Earnings-21 | must be NEUTRAL on score; checked against the null | `wt/obspipe` |
