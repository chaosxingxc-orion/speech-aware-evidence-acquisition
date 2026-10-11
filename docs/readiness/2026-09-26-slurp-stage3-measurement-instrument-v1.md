# The Stage-3 measurement instrument: what this rig can and cannot see

Author: the root coordinator (Fable 5.1), 2026-09-26. Status: **binding for every Stage-3 claim from
this date**. Where an earlier verdict conflicts with this document, this document wins and the earlier
verdict is corrected by its own successor note rather than rewritten. Zero contacts were made to
write it: every number below is read from a sealed arm already in the record.

## 1. Why this document exists

Stage 3 has produced nine mechanism families and not one proven gain. The natural reading is that the
mechanisms are weak. That reading is incomplete: for most of those families the rig could not have
seen a true effect of the size the mechanism produces. The instrument, not the mechanism, has been
the binding constraint, and until it is written down and obeyed the program will keep spending GPU
hours on contrasts whose outcome is decided by flight-to-flight variance.

## 2. The measurements

All numbers are the official SLURP pooled SLU-F1 (micro) and the joint scenario+action intent
accuracy, paired per row, 10,000 bootstrap draws, seed 20260915.

### 2a. Inside ONE flight, the locked plan is nearly deterministic

`SAEA-SLURP-STAGE3-ROLL-AA-V1` (200 R01C rows, the Solver grouped at samples 2 under the
greedy-repeat marker, both samples temperature 0, distinct pinned seeds that greedy decoding does not
consult) — `docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md`:

| quantity | value |
| --- | ---: |
| delivered answer byte-identical between the two passes | 183 / 200 = **91.5 %** |
| delivered intent flips | **0 / 200** |
| entity-set flips | 15 / 200 = 7.5 % |
| paired per-row SLU delta | -0.284 pp, CI95 [-1.096, +0.373] |
| **h_within (SLU / intent) at n = 200** | **0.735 / 0.000** |

### 2b. Across flights, two IDENTICAL requests differ significantly

`SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1` and `SAEA-SLURP-STAGE3-VAR1-PLANR-R01C-V1` are a
request-identical pair: the same 625 R01C rows, the same plan, the same knowledge, the same serving
geometry, two consecutive campaigns of ONE chain (flight commit `3ade29ff`, 2026-09-24 23:48 to
2026-09-25 02:11 UTC). They differ by (`docs/results/2026-09-25-slurp-var1-complete-evidence.md`):

| metric | PLAN | PLANR | difference | CI95 |
| --- | ---: | ---: | ---: | --- |
| pooled SLU-F1 | 58.51 | 60.38 | **+1.87 pp** | **[+0.41, +3.36]** — excludes zero |
| intent | 70.56 | 69.28 | **-1.28 pp** | own-null half-width 1.76 |
| exact entity TP / FP / FN | 345 / 454 / 399 | 366 / 439 / 378 | — | — |

Two facts follow, and they are the most consequential findings of Stage 3's measurement work:

1. **A pure A/A contrast at n = 625 can be statistically significant.** +1.87 pp with a CI95 that
   excludes zero arose from no intervention at all.
2. **The two headline metrics can move in OPPOSITE directions from flight variance alone** (+1.87 SLU
   with -1.28 intent). A verdict that reads one metric as a gain and the other as a loss may be
   reading nothing but the flight.

The mechanism is known and was measured earlier: llama.cpp at temperature 0 is not bitwise
reproducible across batch compositions. Within one flight 8.5 % of rows differ; across flights about
28 % of raw outputs and 5 % of intents differ. With a quarter of the rows moving, a 625-row pooled
metric shifts by one to two points for free.

### 2c. Over ONE sealed sample pool, the floor is small

The aggregation read (`docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md`) compares
delivery rules over the SAME sealed ROLL-1 samples on 625 rows: the medoid rule reads +0.03 pp with
CI95 [-0.63, +0.71], so **h_offline is about 0.67 pp at n = 625**, at zero GPU cost. Nothing is
re-generated, so no flight variance enters.

### 2d. The floor table

| design | n | floor (CI95 half-width, SLU) | flight offset it carries | source |
| --- | ---: | ---: | --- | --- |
| offline read over one sealed sample pool | 625 | **0.67** | none | F1 aggregation read |
| two passes inside one flight (A/A) | 200 | **0.735** (intent 0.000) | none | ROLL-AA |
| cross-flight A/A, construction roster | 625 | 1.474 sampling | **+1.87 measured** | VAR1 PLAN vs PLANR |
| cross-flight A/A, TRAIN Fold A | 1,080 | 1.2485 (intent 0.9943) | +0.17 measured | PLAN vs PLANr |
| cross-flight A/A, DEV-2000-ADDED | 1,000 | 1.2525 (intent 1.1520) | -0.25 measured | B6 pair |
| terminal feedback on 4-16 trajectories | 4-16 | not readable | dominant | batch002 |

**Collection columns (added 2026-10-11).** A column flown only to be READ OFFLINE as material (the typed loop's construction-source lock column,
`docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1/`) declares the design `material-source`: it estimates nothing (no contrast, no twin),
carries no numeric floor, must declare `claims_benefit` false, and is legal at any row count. It is the form-proof rule (section 3 rule 5) for a
cell that is not a four-row structural proof. `stage3_effect_floor_check.py` `FLOOR_TABLE` carries the same entry.

### 2e. DEV-2000-ADDED sealed pool (ROLL-3, 2026-09-27)

`SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1` sealed five temperature-0.7 Solver samples per row (seeds
1249110493 to 1249110497, one flight, the resident np4 geometry) on the 1,000 rows of the evaluation roster
DEV-2000-ADDED, and its registered read `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1` scored each sample
index once under `slurp-slu-official-projected-v3`. The within-pool paired instrument at n = 1,000 -- the
CI95 half-width of a contrast between two sample indices of this pool, over the ten index pairs (whole-utterance
cluster bootstrap, 10,000 draws, seed 20260915):

| contrast | mean | median | range over the ten pairs |
| --- | ---: | ---: | --- |
| per-row intent | **0.82** | 0.71 | 0.65 to 1.09 |
| per-row SLU-F1 | **1.19** | 1.15 | 0.95 to 1.55 |
| pooled micro official SLU-F1 | **1.56** | 1.48 | 1.23 to 2.04 |

The two samples of a pair differ only by seed: pairwise byte identity is 61.46 %, the intent-flip share
5.17 % and the entity-set-flip share 31.41 %; four of the ten pooled micro SLU-F1 contrasts have a CI95 that
excludes zero, none of the ten intent contrasts does. These widths belong to a contrast between two
independent temperature-0.7 draws of one pool; section 2c's 0.67 pp belongs to a delivery rule read against
its own pool. They are different contrasts, so the floor table of section 2d is not amended by them. Read:
`docs/results/2026-09-27-slurp-roll-3-dev2000-added-pool-read.md`.

## 3. The law

1. **Prefer a design with no flight offset.** An action whose effect can be computed over an
   already-sealed sample pool — any selection, commit, projection, verification, re-ranking or
   scoring rule — is read offline at 0.67 pp and costs no GPU. Do this first, always.
2. **Same-flight paired next.** An action that needs new contacts should be compared per row inside
   ONE campaign (the `supply_variants` mechanism of item E42 exists for exactly this and is tested).
   Floor about 0.7 pp. Two prerequisites are open: the family was closed after two aborts, so
   re-authorisation is an owner decision, and `core/bundle/outputs.py` must learn `supply_variants`
   before any number from it is reported.
3. **Cross-flight only with an in-chain A/A replicate, and only for large effects.** A cell that must
   fly cross-flight also flies a request-identical replicate in the same chain. The arm is admitted
   only when its delta's CI95 lower bound is above zero AND the delta exceeds the replicate's own
   measured offset plus that offset's half-width. At n = 625 that bar is about **3 pp**; at
   n = 1,080 about **2.5 pp**.
4. **Never** claim from a single cross-flight contrast against an older sealed comparator with no
   in-chain replicate.
5. **A batch under about 200 rows is a form proof**, never evidence of benefit. Terminal feedback on
   4 to 16 trajectories cannot distinguish any effect this program is chasing.
6. The roster's own null is sealed BEFORE the arm's contrast and never adjusted afterwards.

## 4. What the law corrects in the existing record

- **CELL-3** (gated v2 on DEV-2000-ADDED, -1.44 pp [-2.88, -0.05]) was declared HARMFUL under the
  rule as it then stood. Its in-chain replicate read -0.25 with half-width 1.25, so the arm's loss
  does not exceed the offset bound: the honest reading is **"not distinguishable from flight
  variance"**, not "harmful". Owner decision 111 (close the semantic-delta application line) still
  stands, because it rests on the absence of a demonstrated benefit across four cells, not on that
  single loss.
- **CELL-2 (+0.64), CELL-1 (-0.48) and CELL-1-GEPA (-0.04)** were read cross-flight against a sealed
  comparator with no in-chain replicate. Under rule 4 none of those three numbers supports a verdict
  in either direction; their NEUTRAL labels are consistent with that.
- **VAR-1** is the one family that measured its own offset — it flew PLANR — and therefore read its
  variants correctly: EX-K10 and EX-K30 are +0.07 / +0.09 pp over PLANR, not +1.94 / +1.95 over PLAN.
  The design was right; the lesson is that every cross-flight cell must copy it.
- **VERIFY-1 and the aggregation rules** were read over sealed samples, so their numbers are the
  program's most trustworthy: self-selection intent +0.544 [+0.032, +1.088] and the entity support
  filter +1.40 [+0.55, +2.29] are the only two effects in the Stage-3 record that clear their own
  design's floor.

## 5. What this means for the algorithm, not only for the bookkeeping

The published training-free RL families this program implemented — Training-Free GRPO's semantic
advantage, GEPA's reflective Pareto evolution, ACE's grow-and-refine playbook — share an assumption:
that a candidate update can be evaluated by re-running the task and reading the score. On this rig
that assumption fails. A re-run costs one to three GPU-hours and carries a flight offset larger than
the update's effect. **You cannot climb a gradient you cannot see.** That is the first named
shortcoming of the locked algorithms on these tasks, and it is a property of the rig and the effect
sizes rather than of the tasks.

The improvement follows directly: keep the loop's inner optimisation where measurement is exact. Roll
out once, seal everything, and let credit assignment, candidate selection and the acceptance test all
run over the sealed bytes at 0.67 pp resolution; spend a flight only on the composed policy the
offline loop predicts will clear the cross-flight bar. The action space must therefore be dominated
by actions whose effect is computable from sealed trajectories — selection, verification, commit,
projection, re-ranking of content that was already retrieved — and every action that truly needs new
contacts must be batched into one composed variant instead of being tested one at a time.

## 6. Enforcement

`scripts/checks/stage3_effect_floor_check.py` reads each live cell's preregistration and refuses it
when the declared design's floor exceeds the declared expected effect, when a cross-flight cell
declares no in-chain replicate, or when a cell under 200 rows claims benefit rather than form. The
check is advisory for cells already flown and blocking for new ones.
