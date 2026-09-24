# Cell ROLL-AA read: the within-flight A/A null of the locked v2.0 plan (Stage-3 fast-validation route F2)

Read 2026-09-24 by the coordinator with `scripts/flights/batch/rollaa_read.sh` (driver
`scripts/analysis/stage3_rollout_score.py`, recipe `slurp-stage3-roll-aa-within-flight-null-v1`,
analysis root `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-ROLL-AA-READ-V1`). Model-free: zero
model / tokenizer / encoder / server contacts; the official scorer ran on copies of the two sealed
sample sets. No utterance text, gold or model output is printed.

Status: **DESCRIPTIVE** (a null; no admission, superiority or generalisation claim).

## 1. What flew

Run `SAEA-SLURP-STAGE3-ROLL-AA-V1` / `attempt-slurp-native-stage3-roll-aa-v1-generation`, flight
commit `e50d4088`, SAEA-Batch-Chain-ROLLAA, 2026-09-24 19:35-20:02 UTC: the locked v2.0 plan with
its Solver grouped at **samples 2 under the registered greedy-repeat marker** (temperature 0.0 on
both samples; the harness forces distinct pinned seeds 2080141211 / 2080141212, which greedy
decoding does not consult -- custody check: 200 rows, one temperature set `[0.0, 0.0]`, one seed
set), on the first 200 rows of the construction subset R01C (nine of eighteen scenarios). 1,030
contacts (5.15 per row), 4,064.3 s of repeated speech audio, 8,402,999 prompt / 55,430 completion
tokens, manifest COMPLETED, scored once. Dispositions: revision_limit 1, finite_completion 2,
planner_action_illegal 1. The four-row smoke (20 contacts) was the form proof of the first
temperature-0 Solver group ever flown.

## 2. The null

| quantity | value |
| --- | ---: |
| rows | 200 |
| byte-identical delivered output between the two samples | 183 / 200 = **91.5 %** |
| intent flips (scenario_action) | **0 / 200 = 0.0 %** |
| entity-set flips | 15 / 200 = 7.5 % |
| paired per-row SLU-F1 delta (sample 2 - sample 1) | mean **-0.284 pp**, sd 5.287 |
| CI95 of that delta (row-paired bootstrap, 10,000 draws, seed 20260915) | [-1.096, +0.373] |
| **h_within (SLU)** | **0.735 pp** |
| **h_within (intent)** | **0.000 pp** |

Reported beside it, as context and never as a comparator: the CROSS-flight own nulls, PLAN vs its
request-identical replicate, are h_SLU 1.2485 / h_intent 0.9943 on TRAIN Fold A (n = 1,080) and
h_SLU 1.2525 / h_intent 1.1520 on DEV-2000-ADDED (n = 1,000).

Per stratum the paired intent delta is 0.0 pp in all nine strata; the paired SLU delta is 0.0 in
six and non-zero only in datetime (+0.30), news (-0.62) and one further stratum.

## 3. What it means for the methodology

1. **Inside one flight the locked plan is nearly deterministic.** With byte-identical prompts at
   temperature 0 the delivered answer repeats exactly on 91.5 % of rows and the delivered INTENT
   never changes. The variation that remains is entity-level on 7.5 % of rows.
2. **The diffuseness recorded earlier is a BETWEEN-flight phenomenon.** The program's own-null
   measurements (28 % of raw outputs and 5 % of intents differing under byte-identical prompts)
   compare two separate flights; this read compares two passes inside one flight and finds 8.5 %
   and 0 %. The cross-flight band (about 1.25 pp pooled) is therefore dominated by between-flight
   state -- batch composition across the np4 slots, server state, scheduling order -- not by
   decoding.
3. **Consequence for variant rollouts.** A construction variant compared INSIDE one flight is read
   against h_within (0.735 pp at n = 200; about 0.4 pp at n = 625 by the same per-row sd), while
   the same variant flown as its own campaign is read against the cross-flight own null (about
   1.25 pp). Wherever the harness allows per-row variant interleaving inside one campaign, that is
   where variants should be compared; the VAR-1 family, which flies one campaign per variant, pays
   the between-flight penalty and is read against its own VAR1-PLANR replicate accordingly.
4. **h_within is roster-specific.** This roster covers nine of the eighteen scenarios (the first
   200 rows of R01C in roster order; alarm 17, audio 23, datetime 24, iot 23, music 21, news 30,
   play 13, takeaway 28, weather 21) and per-row variance is scenario-dependent, so h_within
   transfers to another 200-row mixture only as far as the mixtures agree.

## 4. Records

The five ROLL-AA rows are closed in `docs/exposure-ledger.md` (four flight rows plus this read).
The decision receipt is `coordination/slurp-stage3-roll-aa-v1/root-admission-v1.json`
(`slurp-stage3-roll-aa-admission-v1`). The finding is carried into
`docs/handoff/2026-09-24-fable51/HANDOFF-STAGE3-FOR-CHATGPT-v1.md` sections 4 and 7 (route F2) and
sets the engineering item for VAR-2: per-row variant interleaving inside one campaign.
