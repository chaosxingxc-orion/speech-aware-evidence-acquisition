# Three-dimension experiment program on aligned baselines (design, 2026-09-05)

Owner framing (2026-09-05): with the three direct baselines aligned to published results under each dataset's
official scorer, the study now designs a series of experiments along three dimensions through the agent system:
knowledge construction, knowledge consumption, and system evolution. Any paired gain from here is a systemic
improvement over the literature's own numbers, not over a self-made control. This document is the program;
each cell gets its own preregistration before its ledger row. Owner decisions taken the same day: the aligned
one-contact direct cells are the comparators for every mechanism; the frozen core may act as a proposer over
construction rows with their gold on a new text-only D2 arm; construction rosters keep the `discovery` split
role and carry `roster_role = construction`; slice 1 = enablers E1 to E3, prerequisites MF-1 to MF-3, cells
KC-S1a/b, KC-A1, KU-S1/S1c.

## 1. Fixed points

| item | value |
|---|---|
| frozen core | Qwen3-Omni-30B-A3B-Instruct Q4_K_M, llama.cpp featcache 04ccc72a, greedy; Q8_0 excluded by the probe |
| harness | `core.flight.FlightRuntime` (preflight, preprocess, serve, run_phases, seal, score); controller `rails/controllers.py::EvidenceAgentController` over `configs/policy/phase-*.json`; phases run whole-roster through `rails/phase_runner.py::run_program` |
| Audio2Tool comparator | the three official-population manifests (tier 1 500; tiers 2/5/8 1,500; tiers 3/4/6/7 2,000): pooled 61.40, equal-domain 68.11; official scorer `a2t-toolcall-official` (vendored released `metrics.py`), v2 ordered beside |
| SLURP comparator | `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`: scenario 81.0 / action 73.9 / intent 71.4 / SLU-F1 35.8 under the pinned official `evaluate.py`; DEV-500 / NEW500 partition preserved; the locked BLEND arm (83.9 / 77.6 / 75.7 / 41.7) is a reference, not a comparator |
| Earnings-21 comparator | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`: 8.200 Whisper-normalized corpus WER on all 44 calls (whisper-large-v3 9.71); entity WER 30.4 mention-level |
| statistics | `analysis/paired.py::paired_contrast`: delta = arm minus comparator on per-sample official scores; 10,000 replicates stratified by the carrier's strata; seed 20260903; CI90; exact sign test; per-stratum table with the published column; natural-mixture and equal-stratum deltas. ADMITTED = CI90 lower bound > 0 with both weightings agreeing in sign (WER: upper bound < 0); NULL = includes 0 or the weightings disagree; HARMFUL = upper bound < 0 (WER: lower bound > 0) |
| pairing units | Audio2Tool row (strata tier x domain); SLURP utterance (strata scenario; decision population NEW500, pooled 1,000 reported); Earnings window and gold mention with call clusters |
| contact accounting | every two-contact cell reports delta vs the one-contact comparator, delta vs the equal-contact no-knowledge control (`phase-draft-revise-v1`), realized contacts per row, gain per extra contact |
| rules | one factor per cell; pair only against sealed manifests (greedy is not bitwise reproducible across batch shapes); n >= 400; replicate on the same roster before a fresh draw; one experiment in flight; at most one recovery re-registration; construction on TRAIN, USE on DEV, TEST once; gates relative to the published ceiling |

## 2. The three dimensions

| dimension | definition | study vocabulary | the variable |
|---|---|---|---|
| knowledge construction | artifacts built from construction-legal sources (registry, TRAIN, the same call's ConEC document, the block-disjoint construction pool) | ORG | content and organization of the artifact |
| knowledge consumption | how the frozen core is asked to use it: whole prompt, retrieved top-k supply, multi-contact phase programs, verify-revise | SUPPLY + USE | supply form and contact structure |
| system evolution | improving both without parameter updates: the frozen core proposes artifact variants, each is scored by the official scorer on a frozen construction roster, best-of-N is kept, a few rounds | the controller's policy over artifacts | rounds and the selection rule |

Each dimension has a zero: the official-protocol direct baseline (construction), the single whole-prompt contact
(consumption), hand-written artifacts such as ORG-1 (evolution).

## 3. Model-free prerequisites

| id | deliverable | gate |
|---|---|---|
| MF-1 | query-cue audit (`2026-09-05-a2t-query-cue-audit-v1-preregistration.md`): TARGET / DOMAIN-ONLY / LABEL-NOISE / UNCERTAIN per twin pair, same-domain first; error mass per class on the sealed 4,000 misses | KC-A1 only if TARGET pairs carry >= 100 of the 4,000 misses |
| MF-2 | exposure union across every evaluation receipt; reserved `A2T-FRESH-800` (100 per tier, first-successful-speaker rule) never opened before rung 3 | every A2T construction cell; rung 3 |
| MF-3 | SLURP per-intent slot schema from TRAIN (entity types >= 2 % per intent, up to 5 lowercase fillers) as a registered fill; reserved `DEV-500-B` | KC-S1b, KU-S3, EVO-S1; rung 3 |
| MF-4 | per-entity-class ConEC lists per call, Whisper-normalized forms (slice 2) | KC-E1, KU-E1 |
| MF-5 | multi-phase seal path proven by a 4-row dry run per carrier through `run_program` | every two-contact cell |
| MF-6 | DenseCentroid recall@k on construction folds and the 4,000 (slice 2) | KU-A1 only if recall@8 >= 0.85 |

## 4. Cell matrix

### 4a. Knowledge construction

| id | carrier | the one factor | comparator | roster | metrics | budget | decision |
|---|---|---|---|---|---|---|---|
| KC-S1a | SLURP | one added slot-only contact conditioned on the SEALED closed-list intent and the 55-type list, no schema (contact-count control) | closed-list direct | DEV-1000, decide on NEW500 | SLU-F1, entity P/R, Word-F1, Char-F1 per type and scenario; intent identical by construction | 1,008 calls, 0.08 GPU-h | reference for KC-S1b |
| KC-S1b | SLURP | the per-intent TRAIN slot schema added to KC-S1a's contact | closed-list direct; KC-S1a beside | same | same | 1,008, 0.08 | ADMITTED iff LB > 0 vs closed-list and (1b minus 1a) LB > 0; NULL -> USE-2b (self-transcript source); HARMFUL -> slot branch ends |
| KC-A1 | A2T | deterministic contrast notes on MF-1's TARGET pairs appended inline to the compact registry line, shape unchanged | official-protocol 4,000 | the 4,000, strata tier x domain | official tool accuracy with Table 3 per tier, EM, param F1, parse, miss-class table, named pairs before/after | 4,008, 0.75 | ADMITTED -> KC-A1c same-length control; NULL with separability >= 0.80 -> EVO-A1 from the official baseline; HARMFUL -> form/content split recorded |
| KC-A1c | A2T | category word alone appended inline (equal token budget, no contrast content) | official-protocol 4,000 | same | same | 4,000, 0.75 | attributes KC-A1's gain to form or content |
| KC-E1 | E21 | MF-4 per-class lists supplied whole-prompt in the transcribe instruction | E21 full-44 V2 | 44 calls, 1,593 windows, 38,366 mentions | per-class entity recall beside ConEC floor / Whisper-large / oracle; corpus WER beside 9.71; S/D/I | 1,593, 1.1 | ADMITTED = targeted recall LB > 0 and WER delta UB <= 0 |

### 4b. Knowledge consumption

| id | carrier | the one factor | comparator | roster | metrics | budget | decision |
|---|---|---|---|---|---|---|---|
| KU-S1 | SLURP | `phase-direct-evidence-alpha-blend-v1` with the closed-list instruction in both phases, KbFacet top-5, locked alpha 0.45 / tau 0.65 | closed-list direct; sealed BLEND beside | DEV-1000, decide on NEW500 | intent, SLU-F1, realized contacts, gain per extra contact | <= 2,000, 0.15 | ADMITTED -> alpha-blend stays a consumption reference; NULL -> the direct form is the reference |
| KU-S1c | SLURP | `phase-draft-revise-v1`, no knowledge (equal-contact control) | closed-list direct | same | same | 2,000, 0.15 | reported; two-contact deltas are stated net of it |
| KU-S2 | SLURP | whole-prompt TRAIN facets for all 60 intents in one contact | closed-list direct; KU-S1 beside | same | same | 1,000, 0.1 | whole vs retrieved at this k |
| KU-S3 | SLURP | intent-then-slots as one phase program (`phase-intent-then-slots-v1`) | closed-list direct; KC-S1b beside | same | same | 2,000, 0.15 | ADMITTED if SLU-F1 LB > 0 and intent CI90 includes 0 |
| KU-A1 | A2T | one "Likely tools" line from `DenseCentroidProvider` top-8 (audio-keyed, zero core contacts) | official-protocol 4,000 | the 4,000 | tool accuracy (Table 3), EM, F1, parse; split by gold in top-8 | 4,000, 0.75 | gated by MF-6 |
| KU-A2 / A2c | A2T | `phase-select-then-fill-v1` vs `phase-draft-revise-v1` over the compact registry | official-protocol 4,000 | the 4,000 | same + per-phase parse | 8,000 each, 1.4 | only after KU-S3 ADMITTED; ADMITTED if LB > 0 vs direct and vs A2c |
| KU-E1 / E1c / E2 | E21 | retrieved top-20 per window (alpha-blend, stop rule off) vs draft-revise control vs transcribe-then-verify with the whole list | E21 full-44 V2; KC-E1 beside | 44 calls | as KC-E1 plus gain per extra contact | 3,186 each, about 2.0 | as KC-E1's conjunction |

### 4c. System evolution

| id | carrier | the one factor | comparator | roster | metrics | budget | decision |
|---|---|---|---|---|---|---|---|
| EVO-A1 | A2T | the loop of section 5 (R_max 4 rounds on construction folds A/B), then one read | official-protocol 4,000 and the round-0 seed | construction folds, then the frozen 400 per round (curve only) and the 4,000 once | evolution curve; evaluation delta; generalization gap; transfer ratio; Table 3 beside | about 22,000 calls, 4.5 GPU-h | ADMITTED if the 4,000 LB > 0 and the gap <= half the construction gain; NULL if the curve rose but the CI includes 0 (overfitting, selection rule named) or never rose |
| EVO-S1 | SLURP | the same loop code and rule, hash-pinned, on TRAIN folds evolving the per-scenario slot schema | closed-list direct and the seed arm | TRAIN folds, then DEV-1000 once | curve, SLU-F1 and intent deltas, gap | about 10,000, under 1.0 | the generality rung; run regardless of EVO-A1's outcome |
| EVO-E | E21 | none: no construction surface (ConEC is per-call) | | | | 0 | stated as a limit |

## 5. The evolution loop (preregistered constants; the loop's own preregistration cites MF-1)

Targets T from MF-1's TARGET list, disjoint tool sets, at most 12. State `A_r` = description overrides for targeted
tools only; `A_0` = the released compact registry, byte-identical to the sealed baseline. Rendering is always
same-shape: 152 lines `- {signature}: {description}`, plain name sort, no headers; each description <= 200 ASCII
characters; the whole block's token delta over compact is MEASURED and REPORTED, and inside this loop <= +40
tokens over the INCUMBENT as a search budget (see the 2026-09-06 owner ruling below). Per target and round, K = 4
candidates: three proposer rewrites (the `construction-proposer-text` arm; input = the pair's registry rows, M = 8
block-disjoint construction exemplars per tool with their gold calls, the incumbent descriptions; output = the
cue that separates the tools and one description per tool, strict JSON; exemplar draws seeded by (round, target,
k)), one deterministic control (append the domain and category), and in round 1 a length-matched placebo with no
distinguishing cue. Candidate id = sha256 over text, proposer prompt, exemplar ids, round, target, k and family,
pinned by a committed baseline fragment. Candidate k of every target is assembled into one portfolio registry;
a round flies the incumbent plus K portfolios on fold A (20 units per targeted tool plus 120 background rows,
about 600, rows <= 60 s). Selection: per target on fold A admit iff saves >= 4, harms <= 1, net >= 3, winner = max
net; assemble; confirm on fold B: targeted pooled CI90 lower bound > 0, background lower bound >= -1.0 pp, form
caps; accept or keep the incumbent, never partially. R_max = 4; stop after two consecutive rejects or an accepted
gain under 0.5 pp. Per round the incumbent is read on the frozen 400 for the curve only; the final artifact is
read once on the 4,000 paired against the sealed baseline. Headline evidence: the curve (round vs fold-A gain,
fold-B gain, frozen-400 gain), the generalization gap fold-B minus 4,000, and the transfer ratio. Decontamination
per candidate under a model-free ledger row: no shared word 6-gram with any evaluation-roster query text unless
present in the registry; no evaluation ids or gold strings; memorization overlap with the shown exemplars
reported. Preregistered kill results: no target admitted in rounds 1 and 2; a construction gain >= 2 pp whose
4,000 CI90 includes 0 or transfer ratio < 0.25; the deterministic control within 0.5 pp of the proposer; the
placebo indistinguishable; every candidate failing the background tolerance.

**Owner ruling, 2026-09-06 (form cost).** The +40-token headroom is no longer a claim gate. The token delta of
every rendered arm is MEASURED on the flight tokenizer and REPORTED (min / median / p95 / max per arm whenever it
varies row by row, a single figure when it does not); every content artifact flies beside a token- and
structure-matched control -- its **form twin**, matched on the tokenizer rather than on characters -- so form cost
is priced by a flown arm instead of by a cap; and the prompt fit's slot-reserve check is the only hard bound a
rendering has to clear. Inside the evolution loop the +40 survives as a SEARCH budget relative to the incumbent, a
validator constraint that stops the proposer inflating descriptions round after round, and the loop's placebo
family is the form twin of the incumbent. The ruling was taken after KC-A1's lighting artifact measured +44
against an estimated +40 and its character-matched control measured 14 tokens cheaper than the treatment it was
built to price: a cap enforced on an estimate stopped a cell, and a control matched on the wrong quantity would
have mis-attributed it.

## 6. Claim ladder

| rung | statistic | Audio2Tool | SLURP | Earnings |
|---|---|---|---|---|
| 1 admission | CI90 lower bound > 0 on n >= 400 discovery/dev | the 4,000 | NEW500 decision, pooled 1,000 reported | window and mention units, call clusters |
| 2 same-roster replication | re-fly the admitted arm at a different serving geometry: lower bound > 0 again and the point estimate inside rung 1's CI90 | 4,000 | 1,000 to 2,000 | 1,593 windows |
| 3 fresh-roster replication | baseline and mechanism in one registration on the reserved roster | `A2T-FRESH-800`, beside Table 3, both weightings; this is the Audio2Tool confirmatory (no test split exists) | `DEV-500-B` | the rung-4 read |
| 4 confirmatory read, once | one touch, both arms | = rung 3 | official test once (needs the contract amendment the 2026-08-23 rulings name; all 13,078 recordings or headset 2,974: owner) | Earnings-22 confirmatory 109 calls once, after the short-form surface is aligned |
| 5 Stage-3 handoff | sealed manifests, per-stratum tables with published columns, evolution curves, ladder receipts | via `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT` into `papers/<slug>` | | |

Branch-ending results: a HARMFUL cell is dropped with its form/content attribution; two consecutive NULLs on one
dimension of one carrier end that dimension there, with the floor reported beside the published column; a rung-2
failure demotes the mechanism to "observed once"; a rung-3 failure ends the claim.

## 7. Ordering and budget

Slice 1 (approved 2026-09-05): enablers E1 (multi-phase programs through FlightRuntime: seal path, config seam
`phase_material`, `RESPONSE_FORMATS` registry, wire check, prompt fit), E2 (A2T builder registered, exposure union,
registered construction roster with `roster_role`, the proposer arm and its gate), E3 (the loop machinery:
`rails/evolution.py`, `rails/proposer.py`, `evolved-artifact-v1` fill, per-sample score reader), E4 / MF-3 (per-intent
slot schema); MF-5 dry runs; then KC-S1a, KC-S1b, KU-S1c, KU-S1 (SLURP cells are ready first and cheapest, about
0.5 GPU-h together) while MF-1 and MF-2 run on the CPU queue; then KC-A1 (0.75 GPU-h) and KC-A1c if admitted. Slice
2: E5 and MF-4/MF-6, KC-E1, KU-S2/S3, KU-A1, KU-E1 family, EVO-A1, EVO-S1, KU-A2. Whole program: about 94k to 125k
contacts, 19 to 27 GPU-h; Earnings dominates the hours because every arm re-encodes 39 h of audio.

## 8. The paper-facing story

One reward-guided control plane outside a frozen speech-capable core, with the same harness, controller and phase
programs, runs three carriers whose direct baselines were first aligned to the published rows under each dataset's
official scorer. Every mechanism is a single factor paired against a sealed baseline manifest on at least 400
rows, reported under natural-mixture and equal-stratum weightings with the published column beside every stratum,
so an admitted gain is a systemic gain over the literature's own numbers. Knowledge construction, knowledge
consumption and system evolution are the three axes, and the same loop and selection rule are reused across
carriers as the generality test. The evidence for evolution is the round-by-round construction curve and its gap
to the single evaluation read, never a tuned operating point. A four-rung ladder separates what this study can
claim from what the Stage-3 paper repository will confirm.
