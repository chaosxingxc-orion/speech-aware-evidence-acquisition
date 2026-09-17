# Cell B4b verdict: module M4b, the date/time slot-contract revision (slot store v2), on TRAIN A

Status: **ADMITTED** by the preregistered rule, all four clauses passing: pooled SLU +2.55 pp with a
CI95 lower bound of +1.13 pp above zero, intent non-inferior within the 1.0051 pp TRAIN A own null,
projection v3 agreeing in sign, and no scenario losing intent beyond the null band. Root: the B4b
paired-read agent, 2026-09-17. Program:
`docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md` (module M4b, cell B4b).
Preregistration: `docs/readiness/2026-09-17-slurp-b4-org-cells-anchor-v2-preregistration.md`
(section 6, fixed before contact). Margins: the TRAIN A own null of cell B0r, **h_SLU = 1.1218 pp**
and **h_intent = 1.0051 pp** at CI95
(`docs/results/2026-09-17-slurp-b0-review-off-redecision-v2.md`).

## What flew

Run SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-V2, attempt
attempt-slurp-native-slot-store-v2-anchor-train-fold-a-generation-v2, FINALIZED, manifest COMPLETED
at study commit 19ad05b4202622f48c8d604b0cabc5fb6a6b6b83, composed config
8d207b33fa7643b7e5acc4ccbd03354fe9c09df09563544c4879c4bb97ee6a4d, protocol
567a87ad234bb4f17c4735f94219a82b05b25a19d81fdf1ee32bb93b6eda346a -- both equal to the values the
preregistration registers for this cell -- attached to session
serving-slurp-native-candidate-five-train-a-np4-v1, profile `bounded-discovery-probe`. The sealed
dual-store anchor with exactly one ORG channel moved: `knowledge_stores.slot-contracts` repinned from
`knowledge/slurp/semantic/slot-contracts-v1` (release `8a29c48b...`, snapshot `11c246e4...`) to
`slot-contracts-v2` (release `f8e42d4f...`, snapshot `d5992bd1...`), eight of the fifty-four slot cards
changing -- `date`, `time`, `media_type`, `transport_type`, `business_type`, `order_type`, `relation`,
`event_name` -- with all 402 intent bindings byte-identical, so the Perception request was
byte-identical to the anchor's on 1080/1080 contacts and only the Reviewer, Planner and Solver
knowledge blocks moved. Four-row smoke SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-SMOKE-4-V2 sealed
first (composed `c0572352...`, protocol `f13ba493...`, COMPLETED, 20 contacts, 52.98 repeated speech
seconds, 4 task-contract calls, 20 fit receipts, all fits).

| Artifact | SHA-256 |
| --- | --- |
| scores.json | 751c529806e7cd03db13cfba58d583bf7b9d7f14b5b62b6b26e676a5acb308a1 |
| run-manifest.json | b3f7e7ac0babd5ae3e764ad93948203cc40192d72ac3a156b4a479cc69c256ea |
| outputs.jsonl | 01b56d39fa55c48fbdf53e9e9ad5ac4b92428bd9d13a8308a958a7aa0048dfdb |
| paired read `analysis/SAEA-SLURP-B4B-SLOT-STORE-V2-PAIRED-ANALYSIS-V1/score-contrasts.json` | f5ff74c6c56609ead0547b2442ff0f3c1214a1ed63d08e2b43384d41ae384daf |
| paired read `.../README.md` | af43df6f756d70a46734a013746f84d3cd104cf5ad56678c3d6986bc169de24c |
| paired read driver `.../b4b_paired_read.py` | 80d6db58da00bfe1f48d4e2240d2e837bdb4300df3c9b08f02f14c1fa9258ce2 |

Rows: 1,080 scored, 1,079 parsed (1 malformed retained, against the anchor's 7). Comparators, never
re-flown and never re-scored: the sealed anchor
SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1 (primary, scores `7360876322...`) and the
released direct anchor SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1 (secondary, scores
`7840a959fe...`). Paired whole-speaker cluster bootstrap, 10,000 draws, seed 20260915; sensitivity the
paired scenario-stratified row bootstrap on the same draws and seed. Before any table was read, both
comparators reproduced the aggregates the analysis recipe registered before contact, unprojected and
under projection v3, to the hundredth of a point; that STOP condition PASSED.

### Cost and duty cycle

| Figure | B4b | Anchor | Direct | Registered ceiling |
| --- | ---: | ---: | ---: | ---: |
| Generation contacts (per row) | 5,407 (5.006) | 5,417 (5.016) | 1,080 (1.00) | 11,880 (11) |
| Repeated speech seconds | 15,432.81 | 15,459.76 | 3,084.53 | 33,930 |
| Prompt / completion tokens | 47,187,487 / 254,335 | 45,998,267 / 255,153 | 2,459,915 / 26,764 | -- |
| Native task-contract tool calls | 1,075 | 1,082 | 0 | 6,480 |
| FIT receipts / endpoints | 5,407 / 21,628 | -- | -- | -- / 47,520 |
| GPU hours (monitor active seconds) | 3.4651 (12,474.3 s) | 3.3880 | 0.0871 | 12.0 |
| Generation wall seconds | 12,796.8 | not in its receipts | 450.6 | -- |
| Slot occupancy; utilisation; parked | 0.925; 92.43 %; 0.025 | --; 88.73 %; 0.022 | 0.658; 55.66 %; 0.281 | -- |
| Mean latency (s); preprocess (s, workers) | 8.760; 13.68 at 8 | -- | 1.098; 13.03 | -- |
| Official scoring jobs (seconds) | 1 (387.22) | -- | -- | 1 |

Every registered ceiling held with room: 45.5 % of the contact ceiling, 45.5 % of the speech ceiling,
28.9 % of the GPU-hour ceiling, 45.5 % of the FIT-endpoint ceiling and 16.6 % of the task-contract
ceiling. The module adds prompt volume and not contacts, exactly as registered: **+1,189,220 prompt
tokens (+2.59 %) against the anchor for 10 fewer contacts**, and completion tokens fall by 818. FIT:
`every_request_fits = true`, minimum margin **8,242 tokens** in the `reviewer` phase against the
24,576-token slot. One deviation from section 8 to record: the preregistration's model-free bound put
B4b's widest reviewer request at 15,867 tokens (margin 8,709) under the repository's 1.3 word->token
proxy; the realized widest request needed **16,334** tokens, 467 above that bound. Every one of the
5,407 contacts still fit, and the flight's own `build_native_contact_fit_gate` receipts prove it; the
proxy, not the gate, was optimistic.

## B4b minus the sealed anchor (percentage points)

| Metric | Anchor | B4b | Delta | Speaker CI95 | Speaker CI90 | Scenario-stratified CI90 | Equal-scenario | Direct |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: | ---: |
| Official pooled SLU-F1 | 48.53 | 51.09 | **+2.55** | [+1.13, +3.98] | [+1.38, +3.74] | [+1.37, +3.75] | +2.11 | 33.89 |
| Intent (scenario+action) | 77.96 | 78.52 | +0.56 | [-0.71, +1.82] | [-0.51, +1.60] | [-0.46, +1.57] | +0.56 | 73.70 |
| Scenario | 84.81 | 85.09 | +0.28 | [-0.69, +1.25] | [-0.53, +1.09] | [-0.56, +1.11] | +0.28 | 82.69 |
| Action | 79.26 | 79.63 | +0.37 | [-0.96, +1.61] | [-0.72, +1.41] | [-0.56, +1.30] | +0.37 | 75.09 |
| Pooled span F1 | 29.50 | 32.40 | +2.91 | [+0.79, +5.12] | [+1.11, +4.71] | [+1.21, +4.63] | +2.55 | 21.10 |
| Exact slot F1 (row mean) | 19.02 | 20.62 | +1.60 | [+0.30, +2.96] | [+0.52, +2.71] | [+0.51, +2.70] | +1.60 | 10.72 |
| SLU-F1 (row mean) | 30.29 | 31.99 | +1.69 | [+0.66, +2.68] | [+0.82, +2.52] | [+0.78, +2.62] | +1.69 | 16.06 |

Saves / harms / ties with the exact two-sided McNemar p: intent 24 / 18 / 1,038 (p = 0.44); scenario
16 / 13 / 1,051 (0.71); action 22 / 18 / 1,040 (0.64); exact slot F1 63 / 38 / 979 (**0.017**); row
SLU-F1 112 / 58 / 910 (**4.19e-5**). The scenario-stratified sensitivity agrees everywhere: no
interval changes sign.

The shape of the gain is unambiguous. The three label metrics -- intent, scenario, action -- all sit
inside the own null and cannot be claimed. The slot metrics all clear it: pooled SLU-F1, pooled span
F1, per-row exact slot F1 and per-row SLU-F1 each have a CI95 lower bound above zero, and the two
row-level slot metrics also reject their sign tests. This is a slot-contract module that moved slots.

## B4b minus the released direct anchor (secondary)

Pooled SLU +17.20 [+14.00, +20.35]; intent +4.81 [+2.56, +7.04]; scenario +2.41 [+0.19, +4.75];
action +4.54 [+2.36, +6.78]; pooled span F1 +11.31 [+7.89, +14.70]; exact slot F1 row mean +9.91
[+7.89, +12.04]; row SLU-F1 +15.92 [+13.82, +18.16]. Saves / harms: intent 125 / 73 (p = 2.7e-4), row
SLU-F1 327 / 68 (p = 1.0e-41). The system-over-direct margin grows from the anchor's +14.65 to
**+17.20** pooled SLU.

## The rule, applied unchanged

| Clause | Requirement | Value | Margin | Passes |
| --- | --- | ---: | ---: | --- |
| 1, pooled SLU gain | CI95 lower bound of (B4b - anchor) > 0 | +1.1294 | 0 | **YES** |
| 2, intent non-inferiority | CI95 lower bound > -1.0051 | -0.7117 | -1.0051 | **YES** |
| 3, projection v3 agreement | v3 pooled SLU delta agrees in sign | +2.0563 vs +2.5519 | same sign | **YES** |
| 4, scenario band | no scenario's own paired intent delta has a CI95 upper bound below zero | 0 of 18 breaching | CI95 upper < 0 | **YES** |

None of the three HARMFUL triggers fires: the pooled SLU CI95 lower bound is +1.13, far above
-1.1218; the intent CI95 lower bound is -0.71, above -1.0051; and no scenario breaches the band.
**Status ADMITTED.** Read once, from the single official score of the complete manifest; no repeat,
no re-score, no row filtering.

One honesty note on clause 4, since the band was defined before contact and this is its first use.
The band asks for a CI95 upper bound strictly *below* zero. On a 60-row scenario with at most three
harmed rows spread over 36 to 51 speaker clusters, a nonzero share of bootstrap replicates draws none
of the harmed clusters, so the 97.5th percentile pins at exactly 0.00. Five scenarios -- `general`
(-5.00, [-11.32, **+0.00**]), `recommendation` (-5.00, [-11.48, +0.00]), `iot`, `qa` and `takeaway`
(each -1.67, upper bound +0.00) -- sit precisely on that boundary and therefore pass. The clause is
applied exactly as registered and the verdict does not soften it, but the band as written is weak at
this stratum size and the program should say so before it is reused: on 60 rows it can only fire when
a scenario loses on enough distinct clusters that no replicate escapes them.

## Every scenario (natural mixture; equal-scenario mean in the last row)

| Scenario | n | Anchor SLU | B4b SLU | Delta | Anchor intent | B4b intent | Delta | Intent CI95 | Beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| alarm | 60 | 52.66 | 65.76 | **+13.10** | 83.33 | 88.33 | +5.00 | [-1.92, +13.64] | no |
| audio | 60 | 47.75 | 47.32 | -0.44 | 76.67 | 78.33 | +1.67 | [+0.00, +8.57] | no |
| calendar | 60 | 48.38 | 52.06 | +3.68 | 75.00 | 75.00 | 0.00 | [-4.76, +5.17] | no |
| cooking | 60 | 62.47 | 61.76 | -0.72 | 85.00 | 86.67 | +1.67 | [-3.64, +7.14] | no |
| datetime | 60 | 59.52 | 64.31 | +4.80 | 83.33 | 88.33 | +5.00 | [+0.00, +11.11] | no |
| email | 60 | 36.64 | 41.19 | +4.56 | 85.00 | 86.67 | +1.67 | [+0.00, +5.66] | no |
| general | 60 | 15.45 | 12.50 | -2.95 | 36.67 | 31.67 | -5.00 | [-11.32, +0.00] | no |
| iot | 60 | 55.53 | 59.02 | +3.48 | 86.67 | 85.00 | -1.67 | [-5.08, +0.00] | no |
| lists | 60 | 43.55 | 37.81 | **-5.74** | 83.33 | 83.33 | 0.00 | [+0.00, +0.00] | no |
| music | 60 | 34.53 | 36.07 | +1.54 | 76.67 | 78.33 | +1.67 | [-3.70, +7.41] | no |
| news | 60 | 44.24 | 48.90 | +4.66 | 80.00 | 80.00 | 0.00 | [+0.00, +0.00] | no |
| play | 60 | 46.82 | 50.85 | +4.03 | 58.33 | 63.33 | +5.00 | [-6.67, +16.92] | no |
| qa | 60 | 57.04 | 54.98 | -2.05 | 75.00 | 73.33 | -1.67 | [-5.56, +0.00] | no |
| recommendation | 60 | 49.75 | 51.12 | +1.37 | 90.00 | 85.00 | -5.00 | [-11.48, +0.00] | no |
| social | 60 | 34.74 | 40.65 | +5.91 | 66.67 | 66.67 | 0.00 | [+0.00, +0.00] | no |
| takeaway | 60 | 48.84 | 49.14 | +0.30 | 85.00 | 83.33 | -1.67 | [-5.00, +0.00] | no |
| transport | 60 | 51.34 | 52.14 | +0.80 | 86.67 | 86.67 | 0.00 | [+0.00, +0.00] | no |
| weather | 60 | 53.81 | 55.51 | +1.70 | 90.00 | 93.33 | +3.33 | [+0.00, +8.62] | no |
| **equal-scenario mean** | 18 | | | **+2.11** | | | **+0.56** | | |

Thirteen scenarios up and five down on pooled SLU. The extremes are `alarm` **+13.10** and `lists`
**-5.74**; on intent, `alarm`, `datetime` and `play` gain 5.00 while `general` and `recommendation`
lose 5.00 (three harmed rows each). The equal-scenario weighting (+2.11 SLU, +0.56 intent) is close
to the natural mixture (+2.55, +0.56), so the gain is not a single-stratum artifact -- but it is not
uniform either, and `lists` and `general` lose on both readings.

## Projection v3, beside the rule (owner decision 7, and clause 3 here)

| Arm | v3 SLU | v3 intent | v3 scenario | v3 action | v3 span F1 | Labels / fillers changed |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| anchor | 51.99 | 79.35 | 85.46 | 80.65 | 40.30 | 20 / 195 |
| **B4b** | **54.05** | **79.72** | **85.93** | **80.83** | **41.85** | 21 / 170 |
| direct | 34.31 | 75.37 | 84.17 | 75.93 | 23.24 | 47 / 36 |

v3 contrasts: B4b - anchor SLU **+2.06 [+0.53, +3.51]**, intent +0.37 [-0.64, +1.40], span F1 +1.54
[-0.39, +3.39]; B4b - direct SLU +19.74 [+16.27, +23.08], intent +4.35 [+2.12, +6.53], span F1 +18.61
[+14.67, +22.39]. The agreement clause passes on sign and on interval: the v3 pooled SLU gain is also
bounded away from zero. The anchor's and the direct anchor's v3 readings reproduce the registered
51.99 / 79.35 / 85.46 / 80.65 / 40.30 and 34.31 / 75.37 / 84.17 / 75.93 / 23.24 exactly, which is what
licenses reading the arm's v3 number beside them. The projection changes one more label under B4b
(21 against 20) and normalizes **25 fewer fillers** (170 against 195) -- the arm needs less projection
repair than the base, consistent with the contract revision doing part of the projection's work
upstream. The symmetric-normalised scorer `slurp-slu-f1-normalized-v1` still refuses this roster (it
resolves gold from the SLURP `devel` split), exactly as cells B0r and the preregistration recorded;
no TRAIN sibling is registered.

## The M4b diagnostics

Computed with the official scorer's own matching, reconstructed from each arm's sealed outputs. Every
row's reconstruction was checked against that row's sealed official `slu_f1` word and character
counts before any table was built, and the per-type decomposition sums to each arm's official
aggregate (max abs diff 6.8e-13). The A3 audit's anchor baseline -- 81 of 135 gold-date rows omitting,
19 of 72 time rows omitting with 46 non-exact and only 8 of 76 mentions exact, and the six widened
types -- is reproduced exactly from these bytes, so the two columns below are the same instrument.

| Type | Rows with gold | Omits entirely (anchor -> B4b) | All exact | Partial / different | Exact mentions (of gold) | Spurious mentions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| date | 135 | 81 -> **77** | 26 -> 31 | 28 -> 27 | 28 -> **33** of 138 | 7 -> 3 |
| time | 72 | 19 -> **13** | 7 -> **20** | 46 -> 39 | 8 -> **22** of 76 | 11 -> 12 |
| media_type | 57 | 38 -> **29** | 8 -> 11 | 11 -> 17 | 8 -> 11 of 57 | 8 -> 8 |
| transport_type | 36 | 25 -> 24 | 10 -> 11 | 1 -> 1 | 10 -> 11 of 36 | 2 -> 1 |
| business_type | 29 | 22 -> 22 | 2 -> 3 | 5 -> 4 | 2 -> 3 of 29 | 7 -> 8 |
| order_type | 22 | 19 -> **16** | 1 -> 3 | 2 -> 3 | 1 -> 3 of 23 | 7 -> 8 |
| relation | 15 | 15 -> **13** | 0 -> **2** | 0 -> 0 | 0 -> **2** of 16 | 0 -> 0 |
| event_name | 41 | 22 -> 20 | 10 -> 10 | 9 -> 11 | 10 -> 10 of 41 | 13 -> 13 |

Official SLU-F1 mass by type (word and character blocks summed; the last column is the
filler-distance, i.e. surface, mass of the matched spans -- the "time representation loss" the cell was
built to attack):

| Type | FN mass anchor -> B4b | Delta | FP mass anchor -> B4b | Delta | TP anchor -> B4b | Filler-distance mass |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| time | 116.34 -> 83.48 | **-32.86** | 96.34 -> 77.48 | **-18.86** | 110 -> 122 | 74.34 -> 53.48 (**-20.86**) |
| date | 203.58 -> 193.42 | **-10.16** | 49.58 -> 39.42 | **-10.16** | 108 -> 116 | 35.58 -> 33.42 (-2.16) |
| media_type | 95.30 -> 85.82 | -9.49 | 35.30 -> 43.82 | +8.51 | 38 -> 56 | 19.30 -> 27.82 (+8.51) |
| order_type | 44.12 -> 39.99 | -4.12 | 18.12 -> 21.99 | +3.88 | 6 -> 12 | 4.12 -> 5.99 (+1.88) |
| relation | 32.00 -> 28.00 | -4.00 | 0.00 -> 0.00 | 0.00 | 0 -> 4 | 0.00 -> 0.00 (0.00) |
| transport_type | 51.75 -> 49.75 | -2.00 | 5.75 -> 3.75 | -2.00 | 22 -> 24 | 1.75 -> 1.75 (0.00) |
| business_type | 49.47 -> 48.02 | -1.45 | 19.47 -> 20.02 | +0.55 | 14 -> 14 | 5.47 -> 4.02 (-1.45) |
| event_name | 57.58 -> 56.91 | -0.66 | 39.58 -> 42.91 | +3.34 | 38 -> 42 | 13.58 -> 16.91 (+3.34) |

Both registered questions are answered on the instrument that asked them. **Date omission fell**: 81
-> 77 omitting rows, and date's exact mentions rose 28 -> 33 with spurious dates more than halved (7 ->
3), so FN and FP mass both fall by 10.16. **Time representation loss fell hard**: exact time mentions
went 8 -> 22 of 76, all-exact rows 7 -> 20, omitting rows 19 -> 13, and the filler-distance mass -- the
pure representation term -- dropped 74.34 -> 53.48, a 28 % cut. Of the six widened types, all six cut
FN mass and three (`media_type`, `order_type`, `event_name`) bought part of it with new FP mass: the
cards make the core emit where it previously stayed silent, and some of those emissions are wrong.
`relation` moved off zero for the first time (0 -> 4 TP, 2 exact of 16 gold mentions) and
`business_type` did not move its 22 omitting rows at all.

Roster totals, all types: gold mentions 941 (fixed); predicted mentions 910 -> 923; exact mentions
**272 -> 302**; omitted mentions **393 -> 369**; spurious mentions 362 -> 351; filler-distance mass
**814.46 -> 750.76**. The arm emits slightly more, omits less, is wrong less often *and* is closer
when it is wrong.

The cell's one factor does not confine the model's behaviour to the eight cards, and the read says so:
outside the revised set, `radio_name` (-6.40 FN mass), `news_topic` (-5.84), `person` (-4.80) and
`timeofday` (-2.86) improved while `food_type` (+3.78 FN) and `audiobook_name` (+2.00) worsened. Those
are consequences of a changed prompt and of the serving path's temperature-zero batch-composition
nondeterminism, not of any card the v2 store rewrote, and none of them is claimed here.

## The harness-admission consequence

On ADMITTED the B4 runbook (`docs/readiness/2026-09-17-slurp-b4-org-cells-anchor-v2/README.md`, step
7) adds the module to the harness-admission table under the `stores` switch class and to the default
plan. The entry this verdict supports:

- **module**: date/time slot-contract revision (slot store v2)
- **class**: `stores`
- **key**: `knowledge_stores.slot-contracts`
- **on**: release `f8e42d4ff1b220f45b26397340149566544cf5b13d7453fbc46a2b5c3400d11b`, snapshot
  `d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec`
  (`knowledge/slurp/semantic/slot-contracts-v2`)
- **evidence**: this verdict, the sealed score `751c5298...`, the paired read `f5ff74c6...`

**One open point the coordinator must rule on before writing the row.** The `stores` class as
registered in `docs/receipts/harness-admission.json` (v3) defines its OFF arm as the named store
*absent* from the `knowledge_stores` mapping (`rails.config_tables.is_stores_null_arm`), and its proof
as two fragments differing in exactly that one top-level sub-block. Cell B4b's OFF arm is not the
store's absence: it is the anchor's own v1 pin (release `8a29c48b...`, snapshot `11c246e4...`). The two
committed fragments do differ in exactly one top-level `knowledge_stores` sub-block -- and inside it,
in exactly two leaves, the release and snapshot pins, with `candidate_supply`, `store_role` and every
intent binding byte-identical -- but that is a *re-pin* twin, not a null twin. Either the class's null
definition is widened to admit a release/snapshot re-pin as a second legal OFF form, or the entry is
written against a re-pin proof and says so. This verdict does not decide it; the admission receipt is
the coordinator's to close, and `scripts/checks/harness_admission_check.py` is the oracle.

## What is not claimed

- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster; nothing is said about Fold B, DEV-1000 or the test split, which stay unread.
- **No intent, scenario or action gain.** All three sit inside the own null (intent +0.56 with a CI95
  of [-0.71, +1.82] against h_intent 1.0051). The cell is non-inferior on intent and nothing more.
  The +5.00 intent moves in `alarm`, `datetime` and `play` are three-row moves and are not claims.
- **No component-causal attribution below the store.** Eight cards moved together in one release; this
  cell cannot say which card, or which sentence of a card, paid. The per-type table shows where the
  mass moved, not why.
- **Nothing about the revised card language in general.** One frozen core, one roster, one retrieval
  geometry, one release.
- **Nothing about the review loop**, which is held identical to the anchor here; its own decision is
  `docs/results/2026-09-17-slurp-b0-review-off-verdict.md` plus the 2026-09-17 own-null re-decision.
- The A3 row ceilings (81 date rows, 46 time rows) are upper bounds on what a fix could touch, never
  predicted gains; net, the cell moved the date-omission count by 4 of those 81 rows and the
  time-omission count by 6 of 19, and got most of its time gain from representation rather than from
  omission.
- The non-revised entity types that moved are recorded above and explicitly not attributed.

## The twin question

**No twin is registered for cell B4b, and none flew.** The preregistration registers a separation cell
only for B4a (cell B4c, the intent store alone, and only if B4a admits); B4b's single factor needed no
separation cell because the store revision *is* the factor, and the pre-contact request-channel proof
already showed the Perception request byte-identical on all 1,080 rows and the changed set on every
other contact a subset of the eight revised card ids. What B4b has no instrument for is its own
realization noise: the margins used here are cell B0r's own null, measured on the same roster and
geometry but on a *different* configuration (review-off, two contacts per row), and the anchor leg is
a single realization shared with every other cell built on it. The family rule of 2026-09-08 requires
a replicate or a named root cause before a module is frozen, and this verdict is one pass. Two
consequences follow, and the coordinator should register them explicitly:

1. The pooled-SLU gain (+2.55, CI95 lower +1.13) clears h_SLU = 1.1218 by a margin larger than the
   own null's whole half-width, and the slot-level diagnostics give it a mechanism that a batch-order
   difference cannot produce -- 14 more exact time mentions, 30 more exact mentions overall, 64 points
   of filler-distance mass removed. The admission is therefore not a width artifact.
2. It is still **one pass**. A request-identical B4b replicate (about 3.5 GPU hours) would give the
   module its own null and turn "ADMITTED" into "ADMITTED and replicated", as KC-E1f's second pass did
   on 2026-09-09. Nothing downstream should freeze the v2 slot store into a paper-facing claim before
   that, and the default-plan entry should carry the provisional marker until it lands.

Addendum (2026-09-17, owner decision 14): the TRAIN sibling of the symmetric-normalised scorer now exists (`slurp-slu-f1-normalized-v1-train`); the offline re-read `docs/results/2026-09-17-slurp-train-symmetric-reread-v1.md` gives B4b minus anchor **+2.17 pp CI95 [+0.62, +3.68]** symmetric (official +2.55), same sign, so the admission survives normalisation; about 15 % of the official gain is representation alignment; the datetime and alarm scenario gains are mostly surface. The status above is unchanged.
