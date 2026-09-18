# Cell B4b-rep: the request-identical same-roster replicate of cell B4b, preregistration

Status: **PREREGISTERED BEFORE CONTACT.** Author: the B4b replicate registration agent, worktree
`/home/chao/saea-worktrees/fable-b4b-rep`, branch `fable/b4b-rep`, base commit `b4cb9ae9`.
Authority: **owner decision 13 of 2026-09-17**
(`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`) — "a request-identical
same-roster replicate of cell B4b (about 3.5 GPU hours) flies after B2 v3; it yields *ADMITTED and
replicated* and the own null of the admitted configuration" — together with owner decision 15 (the
GPU order), owner decision 17 (the per-scenario harm diagnostic), the family rule of owner Decision 9
of 2026-09-08 item 3, and the iteration rule of 2026-09-03 ("a new mechanism is admitted only after
its predecessor is replicated or root-caused to a named component"). This document grants no model
contact; the cell stays readiness `held` until the coordinator pins the decision receipt and flips it.

Everything recorded here was produced with **zero model, tokenizer, encoder, ASR, scorer and server
contacts**. The resident service was never started, stopped or queried, no run directory was touched,
and no other worktree was modified.

## 1. Why there is a B4b-rep at all

Cell B4b (`SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2`, FINALIZED at study commit
`19ad05b4`, score artifact `751c529806e7cd03db13cfba58d583bf7b9d7f14b5b62b6b26e676a5acb308a1`, run
manifest `b3f7e7ac0babd5ae3e764ad93948203cc40192d72ac3a156b4a479cc69c256ea`) is **ADMITTED**
(`docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md`). All four of its preregistered clauses
passed against the sealed dual-store anchor on 1,080 paired rows:

| clause | requirement | value | passes |
| --- | --- | ---: | --- |
| 1, pooled SLU gain | CI95 lower bound of (B4b − anchor) > 0 | +1.1294 | YES |
| 2, intent non-inferiority | CI95 lower bound > −1.0051 | −0.7117 | YES |
| 3, projection v3 agreement | v3 pooled SLU delta agrees in sign | +2.0563 vs +2.5519 | YES |
| 4, scenario band | no scenario's paired intent delta has a CI95 upper bound below zero | 0 of 18 | YES |

**But it is one pass, and its own verdict says so.** Two facts in that verdict's twin-question section
are the reason this cell exists:

1. **The margins are borrowed from another configuration.** `h_SLU = 1.1218` and
   `h_intent = 1.0051` come from cell B0r
   (`docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`), the TRAIN A own null of the
   **review-off** geometry — same roster, same server, but two contacts per row instead of five and
   no Reviewer or Planner in the graph. Nothing measured the *admitted* configuration's own noise.
2. **The anchor leg is a single realisation** shared with every other cell built on it, and no twin
   was registered for module M4b, because the store revision *is* the factor.

The harness-admission receipt already carries that as a machine-readable obligation. The M4b entry in
`docs/receipts/harness-admission.json` is `"status": "ADMITTED"` with
`"provisional": {"state": "UNMET", "requirement": "replicate on the same roster before the default
plan carries the v2 pins: either a request-identical replicate of this cell (about 3.5 GPU hours) or
the B5 / B5r combination pair..."}`. Owner decision 13 chose the first branch and put it in the GPU
order (decision 15): **B7a → B4b replicate → B4a**. This is that cell, and section 6 is the rule that
closes the obligation.

The precedent is exact and recent: Earnings-21's KC-E1f was admitted provisionally on 2026-09-08 and
replicated request-identically on 2026-09-09
(`docs/readiness/2026-09-09-e21-kc-e1f-replication-v1-verdict.md`), after which the replication was
recorded as a second entry and the first entry stayed. This cell is the SLURP version of that.

## 2. The cell, and why it is a replicate by construction

| item | value |
| --- | --- |
| cell / experiment fragment | `slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2` |
| generation run / attempt | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2` / `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2` |
| native fit run / attempt | `SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-FIT-REPLICATE-V2` / `attempt-slurp-native-slot-store-v2-anchor-train-fold-a-fit-replicate-v2` |
| model fragment | `q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1` (temperature 0, **seed 20260913**, max_tokens 512) |
| dataset fragment | `slurp-speech-native-evo-fold-a-1080` |
| baseline fragment | `slurp-native-anchor-slot-store-v2-train-fold-a-replicate-v2` |
| campaign plan | `configs/campaign/slurp-native-slot-store-v2-anchor-train-fold-a-replicate-v2.json` |
| composed config / protocol | `658c568f335b77ed0612348cc4a79b7dbfa1fee5354deafb999af117f290dbe1` / `b8143a5d9511591cf55da817cc3648c6a644cae309a7c4cf51041fcb035243b2` |
| prepared phase supply | `prepared/SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2/phase-supply-v2.json`, SHA-256 `06e52a88b856e4d60b7d4ed9cda99490d61e5acdb26105e77722489abfe29150`, **output** SHA-256 `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| budgets | 11,880 generation calls, 47,520 FIT endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract calls, one official complete score — **cell B4b's own ceilings, unchanged** |
| session | `serving-slurp-native-candidate-five-train-a-np4-v1`, attach only, never spawn |
| readiness | `held`, carrying the preparation requirement only; the coordinator pins the decision receipt and flips it |

The **baseline fragment is cell B4b's own bytes** with exactly five substitutions: the native-fit run
id, the native-fit attempt id, the two speech-feature identity strings, and the prepared-supply pin —
plus the `what_this_is` prose. The **experiment fragment is cell B4b's own bytes** with the cell, run,
attempt, experiment and fragment-kind identities changed, readiness returned to `held` with the
preparation requirement only, and the prose fields (`purpose`, `decision_population`,
`failure_policy`, the budget `definition`) rewritten to describe a replicate. **The roster, the 1,080
ordered sample ids, the split identity hash, the budgets and every behavioural key are copied, not
retyped.**

Held identical: the arm `speech-feature-query-native-tools`, the policy
`phase-native-candidates-review-revise-v1`, the full native episode with the Reviewer/Planner review
loop **on** (`max_revisions` 1, reviewer `max_iterations` 3, program ceiling 11 contacts), the
Reviewer-only task-contract tool authority and Solver-only answer authority, the candidate contract
(3 candidates, 28 total values, 16 per candidate), the Perception retrieval geometry (k = 8, tau 0.0,
`saea-fuse-associated-values-v1`, `saea-rank-wcos-prior-agree-v1`, the sealed Fold A speech-query
segment vectors and the sealed `SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1` facet vectors), both
knowledge stores with their release and snapshot hashes (`intent-boundaries-v1`,
**`slot-contracts-v2`** at release `f8e42d4f…` / snapshot `d5992bd1…`), every instruction template,
the `phase_tools` block, the scorers, the model fragment, the resident geometry and the promoted
EVO-FOLDS-V2 packets. Fold B is absent.

## 3. The one factor, and what it is not

**The factor is batch composition under greedy decoding, and nothing else.** `llama-server` at
temperature 0 does not return bytes independent of how requests batch across slots, so a cell that
changes nothing at all still produces a non-zero delta. Earnings-21 measured its own version of that
on 1,593 windows; SLURP measured the **review-off** version of it on this roster on 2026-09-17. **The
admitted five-contact review-on configuration has never had that measurement**, and until it does,
module M4b's admission rests on a half-width it did not measure.

Not the media, not the prompt, not the knowledge, not the role graph, not the geometry, not the
population.

### 3.1 Rendered request bytes — proven row for row, before contact

On all 1,080 rows and all four declared phases, cell B4b-rep renders a request **byte-identical** to
cell B4b's, including the `[agent control <program>:<phase>:<sample>]` marker, because the phase
program id does not move. Zero differing rows and a rendered byte delta of exactly 0 in every phase.
The comparison was run three ways through the one authority both the pinned prompt-fit measurement
and `FlightRuntime._verify_phase_prompt_fit` use,
`core.flight.runtime.render_phase_prompt_envelopes`, driven over the whole roster by
`FlightRuntime._phase_prompt_payloads`:

| comparison | rows | differing rows | byte deltas |
| --- | --- | ---: | --- |
| B4b-rep versus cell B4b **as committed on this master** | 1,080 × 4 phases | 0 | {0} |
| B4b-rep versus cell B4b **as flown**, rendered from an export of commit `19ad05b4` with that commit's own code and config bytes | 1,080 × 4 phases | 0 | {0} |
| cell B4b as flown versus cell B4b on this master | 1,080 × 4 phases | 0 | {0} |

Widest envelope per phase, identical in every rendering: perception 77,798 bytes, planner 77,009,
reviewer 77,252, solver 77,969.

Receipt: `SPEECHRL_DATA_DIR/coordination/slurp-b4b-replicate-v2/request-envelope-comparison-v1.json`,
with the per-row, per-phase digests of all three renderings beside it. The third row is what proves
the second matters: `core/flight/runtime.py` and `rails/controllers.py` both changed between the
flight commit and this base (the Node Context Policy engineering landed in that range), and this
pairing shows that drift moves no rendered byte of this cell. The as-flown rendering reproduces cell
B4b's registered composed config hash `8d207b33…` exactly, so the bytes compared are the bytes B4b
sent.

**No identity string reaches a request byte.** Every one of the 4,320 rendered envelopes of every one
of the three renderings was scanned for the run-id prefix
`SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A`, the attempt-id prefix
`attempt-slurp-native-slot-store-v2-anchor-train-fold-a` and the speech-feature identity prefix
`saea-slurp-task-agent-anchor-slot-store-v2`: **0 hits, 12,960 envelopes scanned.** That is what
licenses minting fresh run, attempt, native-fit and speech-feature identities for this cell without
making it something other than a replicate.

The episode-limits epilogue the episode runner appends at dispatch is also identical, because
`max_revisions` and the Reviewer/Planner iteration counts are identical.

### 3.2 The prepared Perception supply — rebuilt, and identical where it counts

`core.preparation.artifact_inputs` binds the composed values (run and attempt ids included) and the
SHA-256 of `rails.kb_policy`, `rails.knowledge_provider`, `rails.phase_supply`,
`rails.knowledge_stores` and `core.flight.runtime`. The run ids necessarily move and
`core.flight.runtime` moved since B4b flew, so the artifact FILE had to be rebuilt model-free for this
cell. Its **output** — the thing that reaches a request — is byte-equal to cell B4b's and to the
sealed anchor preparation's:

| artifact | file SHA-256 | output SHA-256 |
| --- | --- | --- |
| B4b-rep | `06e52a88b856e4d60b7d4ed9cda99490d61e5acdb26105e77722489abfe29150` | `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| B4b | `13d0a8c91e7b5a35cdda6691ee383b18cc3a025d38bf9f3d149ae0ece859f685` | `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |
| anchor | `c5b0b51c23ef22feb1284559cd9e37286922d4cefc2e3cfcf7feafb23e3b595e` | `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` |

1,080 of 1,080 rows select the identical ordered value ids in every pairing. Receipt:
`SPEECHRL_DATA_DIR/coordination/slurp-b4b-replicate-v2/phase-supply-vs-b4b-and-anchor-v1.json`.

### 3.3 What cannot be held fixed, named here rather than discovered later

1. **Batch composition.** Four slots and about 5,400 contacts; `id_slot` is per-sample, so which
   requests share a decode batch depends on arrival timing. This is the factor.
2. **The serving process instance.** Cell B4b ran under this same resident session;
   `core.session.attach_session` identity-checks the binary SHA-256, both GGUF SHA-256 values,
   `-c 98304 -np 4`, the four 24,576-token slots and the speech-feature root before the first
   contact, so the *server* is the same server and only the process instance may differ.
3. **The realized contact count.** The episode is adaptive: B4b realized 5,407 contacts against the
   anchor's 5,417. A replicate may realize a slightly different number, and that difference is part
   of what this cell measures, not a defect.

### 3.4 The identity anchor is a STOP condition, not a report line

The composed config hash of a replicate **necessarily** moves, because the run and attempt ids are
inside it. What must not move is the behaviour, and section 3.1 is what proves that. Before the first
contact the coordinator re-runs `core.flight.cli check` and confirms the runtime-derived protocol
hash equals the hash registered at that moment (the pre-flip value is
`b8143a5d9511591cf55da817cc3648c6a644cae309a7c4cf51041fcb035243b2`; the re-pin cycle of the runbook
replaces it in one place and rewrites every document that quotes it). If it differs by one character,
the flight stops and reports.

The hashing method itself is verified twice on this checkout: the same `compose()` /
`protocol_hash()` call reproduces cell B4b's own `8d207b33…` / `567a87ad…` — the values its
preregistration registered and its verdict records as flown — and the sealed anchor's registered
protocol hash `d1c61c09102dcb8801ea134d763fca0b5b60054d6ef80a3a38752642c107c87d`.

### 3.5 One deliberate difference from cell B0r, named rather than buried

Cell B0r **held** the WAVE R7 speech-feature identity strings at cell B0's values, on the argument
that a replicate that renamed them would not be a replicate. This cell **mints fresh ones**
(`saea-slurp-task-agent-anchor-slot-store-v2-replicate-v2` and its `:query-speech` sibling), on the
instruction of the registration brief, and the two positions are reconciled by measurement rather
than by assertion: section 3.1's scan proves the strings appear in **none** of the 12,960 rendered
envelopes, `core.model.transport` validates and drops them, and native contact-fit receipts are
namespaced by the FIT run and attempt id, so neither holding them nor minting them can change a
request byte or collide with B4b's receipts. Minting them is the stricter choice for provenance — this
cell's speech-feature receipts are addressable as its own — and it costs nothing the core can see.

## 4. Metrics

Primary: **official pooled SLU micro F1** from `slurp-slu-official-train` (pinned official
`evaluate.py`, `slurp-official-8eb16545`), natural mixture, one complete score per manifest through
`core.scoring_batch`, never sharded.

Secondary gate: intent (joint scenario+action) accuracy. Agreement reading: **projection v3**
(`slurp-slu-official-projected-v3-train`), owner decision 7 of 2026-09-17, reported beside every
official number.

Secondaries: scenario accuracy, action accuracy, official pooled span F1, per-row mean official
SLU-F1, per-row mean exact slot F1, saves/harms/ties with the exact two-sided McNemar p, and the count
of rows whose delivered (scenario, action) pair differs between the two passes.

Mandatory diagnostics: the per-type `date`, `time`, `media_type`, `transport_type`, `business_type`,
`order_type`, `relation` and `event_name` false-negative and false-positive decomposition of the B4b
verdict, recomputed on **this cell's own sealed outputs** with the official scorer's own matching; and
the owner-decision-17 net-harmed-rows-per-scenario count.

Two signed contrasts: the **clauses** use `delta = R minus the sealed anchor`; the **own null** uses
`delta = R minus cell B4b`. Both in percentage points, negative meaning worse.

## 5. Resampling and tables

Paired whole-speaker cluster bootstrap, **10,000 draws, seed 20260915**, CI95 for the clauses and
CI90 for diagnostics, both as percentile pairs of the same retained replicate sequence — cell B4b's
own estimator settings, unchanged. Sensitivity: paired scenario-stratified row bootstrap, same draws
and seed. Speaker clusters (125) come from the released roster metadata
(`analysis/SAEA-SLURP-TRAIN-A-DIRECT-ANCHOR-RELEASE-PAIRED-ANALYSIS-V1/roster-metadata.json`,
SHA-256 `07f4cd83b83d83d65500a328e0a38421ede575195c63ae118def0d1006c14e34`). Every verdict carries
the 18-scenario table in both the natural-mixture and the equal-scenario weighting.

**STOP condition.** Before any table of this cell is read, the recomputed `(B4b minus anchor)`
contrast must reproduce the first pass's CI95 lower bounds **+1.1294** (pooled SLU) and **−0.7117**
(intent) to the digit, and both comparators must reproduce their registered official and
projection-v3 aggregates (anchor 48.53 / 77.96 / 84.81 / 79.26 / 29.50 and 51.99 / 79.35 / 85.46 /
80.65 / 40.30; direct 33.89 / 73.70 / 82.69 / 75.09 / 21.10 and 34.31 / 75.37 / 84.17 / 75.93 /
23.24). If they do not, the read stops: the same sealed bytes under the same estimator and seed cannot
give two answers.

## 6. Decision rule (fixed here, before the replicate is read)

> **Replication of module M4b (the date/time slot-contract revision, slot store v2) on TRAIN Fold A.**
> Let R be this replicate, B4b the first pass and A the sealed dual-store anchor, all on the same
> 1,080 rows with the same paired whole-speaker cluster bootstrap (10,000 draws, seed 20260915).
>
> **Clause 1 — the replication clause.** R is **REPLICATED** if and only if all three of the clauses
> cell B4b passed hold for R, applied unchanged: (a) the CI95 lower bound of the official pooled SLU
> micro F1 delta `(R − A)` is **greater than 0**; (b) intent is **non-inferior within 1.0051 pp** —
> the CI95 lower bound of the intent delta `(R − A)` exceeds −1.0051; (c) the **projection-v3**
> reading of the pooled SLU delta **agrees in sign** with the unprojected one. Read **exactly once**,
> from the single official score of the complete manifest.
>
> **Clause 2 — the own null of the admitted configuration.** `h_SLU_M4b` and `h_intent_M4b` are the
> CI95 half-widths of `(R − B4b)` for pooled SLU and intent respectively, on the same rows at the
> same interval level. They are **outputs of this cell, not inputs**: no value for either is written
> anywhere in this registration and neither may be chosen after the fact. They are reported beside
> the B0r-measured **1.1218** and **1.0051**, which are the review-off configuration's half-widths
> that cell B4b had to borrow.
>
> **Clause 3 — the consequence.** On **REPLICATED**, the provisional obligation of the M4b
> harness-admission entry is **MET**: a second entry records the replication, the first entry stays
> (as the KC-E1f v1/v2 pair does), and the SLURP default plan **may** carry the `slot-contracts-v2`
> release and snapshot pins. If clause 1 fails, the entry **stays provisional with its obligation
> UNMET**, the default plan keeps the v1 pins, and **the owner is told**. **No third pass** of this
> configuration is registered or authorized either way.
>
> **Clause 4 — mandatory tables.** The full 18-scenario table in both the natural-mixture and the
> equal-scenario weighting, plus the owner-decision-17 diagnostic — **net harmed rows per scenario,
> with any scenario at five or more flagged** — for both the `(R − A)` and the `(R − B4b)` contrasts.
>
> **Clause 5 — the symmetric scorer.** If the TRAIN sibling of `slurp-slu-f1-normalized-v1` that
> owner decision 14 orders is registered by the time this cell is read, its numbers are reported
> beside every official number; if it is not, "not evaluable on TRAIN" stays the honest statement,
> exactly as cells B0r and B4b recorded. It is never a gate here.
>
> Diagnostics reported beside the rule and never used for it: the `(R − B4b)` point estimates,
> saves/harms/ties with the exact two-sided McNemar p, the per-type slot decomposition recomputed on
> R's own sealed outputs, cell B4b's own clause-4 per-scenario intent band, and R's contacts, GPU
> hours and duty cycle.

Four properties of that rule are deliberate and are recorded here so no later reader has to infer
them.

1. **Clause 1 is B4b's rule, not a new one.** A replication that moved the bar would not be a
   replication. The three conjuncts, the −1.0051 margin, the estimator, the draws and the seed are
   copied from `docs/readiness/2026-09-17-slurp-b4-org-cells-anchor-v2-preregistration.md` section 6.
2. **Clause 1 does not restate B4b's clause 4.** The brief that commissioned this cell names three
   conjuncts. B4b's fourth clause — the per-scenario intent band — is **reported, not gated**, and
   clause 4 here is why: the B4b verdict's own honesty note showed the band is weak at 60-row strata
   (five scenarios pinned at an upper bound of exactly +0.00), and owner decision 17 answered that by
   ordering the net-harmed-rows diagnostic in every paired read rather than by changing the
   registered rules. This package therefore carries **both** — B4b's band as a diagnostic and owner
   decision 17's count as the mandatory table — and gates on neither. That is a deliberate,
   brief-directed scoping of the gate, stated here so it is not read later as a silent drop.
3. **The half-widths are outputs.** No value of `h_SLU_M4b` or `h_intent_M4b` appears in this
   document. The 1.1218 and 1.0051 quoted above are cell B0r's review-off measurements, quoted only
   to say what this cell replaces; they gate nothing here.
4. **One replicate, not a family.** A third pass of this configuration would be repeat-to-pass and is
   neither registered nor authorized, whichever way clause 1 falls.

## 7. Cost reporting (mandatory in the verdict)

- actual generation contacts, against cell B4b's realized **5,407** (5.006 per row) and the anchor's
  5,417 (5.016); the ceiling is 11 per row, 11,880 per cell;
- contacts per row;
- actual repeated speech seconds, against B4b's realized **15,432.81** and the ceiling 33,930;
- actual FIT endpoints, 4 per realized contact, against B4b's **21,628** and the ceiling 47,520;
- actual native task-contract tool calls, against B4b's **1,075** and the ceiling 6,480;
- GPU hours read from the serving monitor
  (`SPEECHRL_DATA_DIR/serving/serving-slurp-native-candidate-five-train-a-np4-v1/monitor.jsonl`)
  over the lease window, never a wall-clock guess, against B4b's measured **3.4651** (12,474.3
  monitor active seconds);
- mean latency, slot occupancy, utilisation and parked fraction from the same monitor, against
  B4b's 8.760 s, 0.925, 92.43 % and 0.025;
- generation wall seconds against B4b's 12,796.8; preprocess and official scoring wall time against
  B4b's 13.68 s at 8 workers and 387.22 s;
- prompt and completion tokens from this cell's own sealed fit receipts, against B4b's
  **47,187,487 / 254,335**;
- the minimum FIT margin, against B4b's **8,242** tokens in the `reviewer` phase.

Registered ceilings, which are bounds and not targets: **11,880 generation calls, 47,520 FIT
endpoints, 33,930 repeated speech seconds, 12.0 fit-inclusive GPU hours, 6,480 native task-contract
calls**, one official complete scoring job, zero ASR, encoder and paid-API calls. Expect roughly 3.5
GPU hours and about 3.5 hours of generation wall clock, from B4b's measured 12,796.8 s.

## 8. Prompt fit

Model-free estimate from `core.flight.cli check` over the widest request each phase renders across the
whole roster, against the 24,576-token serving slot: perception 19,992 required window tokens
(operational margin 4,584), reviewer 19,856 (4,720), planner 19,795 (4,781), solver 20,035 (4,541) —
decision **ALLOW** for every phase. These are cell B4b's own numbers to the token, because the
envelopes are the same envelopes.

The measured truth for the contacts that actually fly comes from cell B4b's **5,407 sealed native
contact-fit receipts**: `every_request_fits = true`, minimum margin **8,242** tokens in the `reviewer`
phase, widest realized reviewer request **16,334** tokens. Because the rendered request is
byte-identical row for row, those receipts bound this cell too.

**One honest carry-forward.** The B4 anchor-v2 package's model-free proxy put B4b's widest reviewer
request at 15,867 tokens under the repository's 1.3 word→token factor; the realized maximum was 467
tokens higher. Every contact still fit, and the flight's own `build_native_contact_fit_gate` receipts
proved it — the proxy, not the gate, was optimistic. This package records that rather than repeating
the proxy as a prediction.

## 9. No smoke, and why

No four-row smoke is registered, and none is needed. The request bytes of this cell **are** cell
B4b's, proved row for row in section 3.1 before any contact. B4b's own smoke
`SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-SMOKE-4-V2` (composed `c0572352…`, protocol `f13ba493…`,
COMPLETED, 20 contacts, 52.98 repeated speech seconds, 4 task-contract calls, 20 fit receipts, all
fitting) already sealed the structural form of this exact episode. Re-flying it would spend contacts
to re-learn a fact already on file, and — worse — would put four rows of this roster through a second
batch composition before the measurement this cell exists to make.

The structural assertions still hold at the campaign's own seal, and the coordinator checks them
there: about 5,400 contacts within the 11,880 ceiling, the Reviewer/Planner loop present on the rows
that trigger it, one `*.request-fit.json` per realized contact with `every_request_fits = true`, and
the exact ordered 1,080 outputs.

## 10. Failure rule

The first failure stops the cell and preserves everything. No automatic restart, replay, row
filtering, roster, role-graph, prompt, geometry or cap change, and no silent recovery. At most one
root-diagnosed recovery re-registration; a second failure closes the flight and the fix must be proven
on a four-row dry run before another mechanism is admitted. A partial manifest is never scored and
never read. One experiment in flight at a time.

## 11. What is NOT claimed

- **No new claim about module M4b's effect size.** This cell re-applies B4b's own clauses to a second
  realisation and measures the configuration's own noise. It does not enlarge, re-estimate, average
  or replace the first pass's numbers, and the first verdict stands unchanged beside the replication
  verdict.
- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster; nothing is said about Fold B, DEV-1000 or the test split, which stay unread.
- **No component-causal attribution below the store.** Eight cards moved together in one release;
  neither pass can say which card, or which sentence of a card, paid.
- **Nothing about the review loop**, which is held identical to the anchor here; its own decision is
  `docs/results/2026-09-17-slurp-b0-review-off-verdict.md` plus the 2026-09-17 own-null re-decision.
- **Nothing about the non-revised slot types** that moved in the first pass; they were recorded there
  as unattributed and stay unattributed here.
- **A REPLICATED verdict admits the v2 pins into the default plan; it does not admit them into a
  paper.** Stage-3 claims belong to a separately admitted paper repository.
- **This cell measures its own noise, not a general one.** `h_SLU_M4b` and `h_intent_M4b` belong to
  this configuration, this roster and this serving geometry; they are not a SLURP-wide constant and
  must not be imported into another cell the way the DEV-1000 half-widths once were.
- **The 3.5 GPU hours this cell spends buy a margin, not a result.** Even a REPLICATED verdict leaves
  every claim boundary of the first verdict exactly where it was.

## 12. Analysis recipe

`docs/readiness/2026-09-17-slurp-b4b-replicate-v2/analysis-recipe-v1.json` pins the four score
artifacts (three sealed, one to be filled in by the coordinator after the manifest seals), the roster
metadata, the shared estimators (`analysis.null_calibration_cli.rows_for`,
`analysis.null_calibration.pooled_f1`, `analysis.paired.resampled_statistic`,
`analysis.paired.paired_contrast`), the seed, the draws, the two interval levels, the four contrasts,
the required tables and the decision rule of section 6. It reuses the released paired-read tooling
rather than a private reimplementation; `analysis.score_compare_cli` is deliberately not the runner
because it hard-codes CI90 and DEV population names.

Outputs:
`analysis/SAEA-SLURP-B4B-REPLICATE-OWN-NULL-PAIRED-ANALYSIS-V1/{score-contrasts.json,README.md}` and
the verdict `docs/results/2026-09-17-slurp-b4b-replication-v2-verdict.md`. The first-pass verdict
`docs/results/2026-09-17-slurp-b4b-slot-store-v2-verdict.md` stays on record beside it.

## 13. Pre-contact evidence on file

All under `SPEECHRL_DATA_DIR/coordination/slurp-b4b-replicate-v2/`, outside the repository so no
receipt can dirty the tree the scoring gate reads at finalize. The SHA-256 of each is recorded in
[`2026-09-17-slurp-b4b-replicate-v2/README.md`](2026-09-17-slurp-b4b-replicate-v2/README.md)
section 6.

| receipt | what it proves |
| --- | --- |
| `prepare-supply-v1.json` | the model-free supply preparation receipt for this cell, `contact_class = model-free` |
| `phase-supply-vs-b4b-and-anchor-v1.json` | the rebuilt Perception supply selects what cell B4b and the sealed anchor selected, on 1,080/1,080 rows, and all three artifacts share the output digest `ba5e1faa…` |
| `composed-hashes-v1.json` | the composed and protocol hashes, and the method verification against cell B4b's registered `8d207b33` / `567a87ad` and the sealed anchor's registered `d1c61c09` |
| `request-envelope-comparison-v1.json` | byte-identical rendered requests on 1,080 rows × 4 phases in all three pairings, with 0 identity-string hits in 12,960 scanned envelopes |
| `request-envelope-digests-b4b-replicate-v1.json`, `request-envelope-digests-b4b-v1.json`, `request-envelope-digests-b4b-asflown-v1.json` | the per-row, per-phase envelope digests behind that claim |
| `plan-hashes-v1.txt` | the SHA-256 of every plan and protocol document in the readiness directory |
| `ledger-parse-v1.json` | `contracts._parse_ledger_tables` sees both rows exactly once, each `consumed = no` |
| `check-v1.json` | `core.flight.cli check` passes: gate, exposure row, clean tree, attempt free, prompt budget ALLOW for every phase |

`core.flight.cli wire-check` is unavailable for any native-episode cell:
`FlightRuntime._dispatch_phase_program` refuses a native episode whose transport is not the real
shared speech renderer, and `wire_check` installs a text transport double. Cell B4b, cell B0r and the
sealed anchor declare the same stages for the same reason. The row-for-row envelope comparison of
section 3.1 is the contact-free substitute and is stronger per row.
