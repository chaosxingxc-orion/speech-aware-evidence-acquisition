# Cell B1r verdict: the request-identical replicate of module M1, the speech-keyed exemplar supply, on TRAIN A

Status: **REPLICATED.** All three clauses of the preregistered rule hold on the second realisation,
applied unchanged: pooled official SLU-F1 against the sealed dual-store anchor **+13.70 pp with a
CI95 lower bound of +11.64 above zero**, intent **+2.13 pp [+0.81, +3.38]** whose lower bound clears
the -1.0051 non-inferiority margin, and the projection-v3 reading **+11.98 pp** agreeing in sign
(the TRAIN symmetric sibling agrees too, at +12.26). The cell also
delivers the thing the program needed more than the verdict: **the exemplar-supplied configuration's
own null, h_SLU_M1 = 1.2350 pp and h_intent_M1 = 1.2212 pp**, measured rather than borrowed. Root:
the B1r paired-read agent, 2026-09-19. Preregistration:
`docs/readiness/2026-09-19-slurp-b1-replicate-v1-preregistration.md` (sections 4-7, fixed before
contact); recipe `docs/readiness/2026-09-19-slurp-b1-replicate-v1/analysis-recipe-v1.json`
(`88f085ac...`). Authority: **owner decision 37** of 2026-09-19 ("follow your recommendation": a
request-identical replicate of cell B1 flies before the base lock closes, and module M1 enters the
default plan only if it replicates) and **owner decision 38** (a contrast involving a configuration
uses that configuration's own request-identical replicate's margins).

Read **once**, from the single official score of the complete manifest. No repeat, no re-score, no
row filtering, **no third pass**.

## What flew

One attempt, FINALIZED on the first pass. Run `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-V1`,
attempt `attempt-slurp-native-exemplars-k20-anchor-replicate-train-fold-a-generation-v1`, manifest
**COMPLETED** at study commit `c905ddf01dbb6e9c2e62cf154a413add3bf0c506` with **empty dirt**,
composed config `130a72f658a3d30d549d06745db4ef7cd1bacafbb9dc378f81be2246fe776150`, protocol
`9c17b1723917f8ea67b8b454967d4ef15e8cd7b6fbb45d149e60a537723a1cd7` -- both the values the package
registers -- arm `speech-feature-query-native-tools`, profile `bounded-discovery-probe`, split
identity `61b0f062...`, role `discovery`, 1,080 distinct rows, one official complete scoring job,
created 2026-09-19T20:52:46Z, attached to session
`serving-slurp-native-candidate-five-train-a-np4-v1`.

| Artifact | SHA-256 |
| --- | --- |
| run-manifest.json | `3d4946e0786b07f76637d25427751435aa210d3b0aab0df11ca3f93919001016` |
| scores.json | `2024b3de1d3822c2f7b966936210fdc594bd54538b58cc30813e271f0cbd0c10` |
| outputs.jsonl | `f49d0ad9defc8e319346e41f62a9c4988500e2e9a7b2d87c34cc79f391006963` |
| trace.jsonl | `470cb40d26871ccbf9041f22b7817104c1fb09914184c413f80daebe8a6fb464` |
| flight-receipts.json (file) | `43766d99e8aea28fb88caa1e0901283eec5aed4305aa9a0784112646475f0b17` |
| flight-receipts.json (its own `receipts_hash`) | `88a1ec43b18cb8fb360587355ec47ab375e430db7db2eb01c04bb4defe341b32` |
| phases.json | `34938d958794869d673586b66bc9ffc8e39ea172ab7d80b2a301c34d8356f8b1` |

The phase artefact binds one system on both passes: policy and controller
`phase-native-candidates-review-revise-v1`, executor `openjiuwen-workflow-v1`, knowledge snapshot
`a43d8b93f93c4c6d294c8f23b7aa0dd5cc340d00d566bff88880d931ddf3ef80` -- cell B1's own snapshot digest,
identical, against the anchor's `4e74d0d7...`.

Rows: 1,080 scored, **1,078 parsed** (2 malformed retained, against cell B1's 4 and the anchor's 7).
Comparators, never re-flown and never re-scored: the sealed anchor
`SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1` (the clause comparator, scores
`7360876322...`), cell B1's own sealed recovery arm
`SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2` (the own-null comparator, scores
`a7105b3285...`) and the released direct anchor `SAEA-SLURP-DIRECT-MAX512-TRAIN-FOLD-A-SOURCE-RECOVERY-V1`
(secondary, scores `7840a959fe...`). All four carry the pinned official scorer
`slurp-official-8eb16545` (evaluator commit `8eb16545762b...`), all four pass its port/official
identity check, and none carries a label projection on its decision score.

Estimator: paired whole-speaker cluster bootstrap over the roster's **125** speaker clusters,
**10,000 draws, seed 20260915**, CI95 for the clauses and CI90 beside; sensitivity the paired
scenario-stratified row bootstrap on the same draws and seed. Every table below is carried in both
the natural-mixture and the equal-scenario weighting.

## The STOP condition PASSED before any B1r table was read

Both halves, from the sealed bytes:

- the three registered comparator aggregates reproduce to the hundredth -- anchor
  48.53 / 77.96 / 84.81 / 79.26 / 29.50 and cell B1 61.14 / 80.19 / 86.39 / 81.39 / 48.43 and direct
  33.89 / 73.70 / 82.69 / 75.09 / 21.10;
- cell B1's **whole sealed verdict table** reproduces to the hundredth on all seven headline rows
  and on every saves / harms / ties triple -- **50 individual field checks across 7 rows, 0
  failures** -- including its registered four-decimal clause values **+10.5381** (pooled SLU CI95
  lower; recomputed 10.538098) and **+0.7407** (intent CI95 lower; recomputed 0.740741), both within
  the recipe's 1e-4 tolerance.

`analysis.null_calibration.pooled_f1` also reproduces every arm's own official aggregate to better
than 1e-6 before any contrast is formed.

## B1r minus the sealed anchor (the clause contrast, percentage points)

| Metric | Anchor | B1r | Delta | Speaker CI95 | Speaker CI90 | Scenario-stratified CI90 | Equal-scenario | Cell B1's first pass |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: | ---: |
| Official pooled SLU-F1 | 48.53 | **62.23** | **+13.70** | [+11.64, +15.73] | [+11.98, +15.40] | [+12.01, +15.38] | +13.67 | +12.61 [+10.54, +14.60] |
| Intent (scenario+action) | 77.96 | 80.09 | **+2.13** | [+0.81, +3.38] | [+1.04, +3.17] | [+0.93, +3.33] | +2.13 | +2.22 [+0.74, +3.71] |
| Scenario | 84.81 | 86.85 | +2.04 | [+0.97, +3.06] | [+1.14, +2.89] | [+1.02, +3.15] | +2.04 | +1.57 [+0.57, +2.53] |
| Action | 79.26 | 81.02 | +1.76 | [+0.48, +2.98] | [+0.70, +2.79] | [+0.56, +2.96] | +1.76 | +2.13 [+0.64, +3.56] |
| Pooled span F1 | 29.50 | **49.92** | **+20.43** | [+17.46, +23.35] | [+17.96, +22.88] | [+17.86, +23.00] | +19.91 | +18.93 [+15.93, +21.76] |
| Exact slot F1 (row mean) | 19.02 | 32.46 | **+13.44** | [+11.48, +15.52] | [+11.78, +15.19] | [+11.70, +15.23] | +13.44 | +12.33 [+10.38, +14.36] |
| SLU-F1 (row mean) | 30.29 | 41.36 | **+11.06** | [+9.37, +12.81] | [+9.65, +12.52] | [+9.66, +12.45] | +11.06 | +9.85 [+8.19, +11.55] |

Saves / harms / ties with the exact two-sided McNemar p: intent 44 / 21 / 1,015 (**5.92e-3**);
scenario 36 / 14 / 1,030 (**2.60e-3**); action 41 / 22 / 1,017 (**2.26e-2**); exact slot F1
220 / 32 / 828 (**1.10e-35**); row SLU-F1 273 / 57 / 750 (**5.99e-35**). The scenario-stratified
sensitivity agrees everywhere: no interval changes sign and none of the seven contains zero.

**The second realisation is, if anything, a little stronger than the first** -- +13.70 against
+12.61 on the primary, +20.43 against +18.93 on span F1 -- and the two intervals overlap over almost
their whole length. Nothing here revises cell B1's numbers; the first verdict stands unchanged beside
this one.

## B1r minus the released direct anchor (secondary, reported and never gating)

Pooled SLU **+28.35 [+24.99, +31.76]**; intent +6.39 [+4.26, +8.63]; scenario +4.17 [+2.09, +6.36];
action +5.93 [+3.79, +8.22]; pooled span F1 +28.83 [+24.94, +32.87]; exact slot F1 row mean +21.74
[+19.21, +24.41]; row SLU-F1 +25.30 [+22.80, +27.98]. Saves / harms: intent 132 / 63 (p = 8.7e-7),
row SLU-F1 417 / 53 (p = 3.5e-71). The system-over-direct margin on pooled SLU is **+28.35** against
cell B1's own +27.25. No scenario loses intent beyond the band on this contrast either (0 of 18), but
owner decision 17's net-harmed diagnostic fires on one: `general`, net +6 harmed rows on intent
(delta -10.00, CI95 [-24.67, +3.92]). Against the direct anchor the band and the flag are reported,
not gating -- the same note cell B1's verdict made about `alarm`.

## Clause 2: the own null of the admitted configuration (OUTPUTS)

`h_SLU_M1` and `h_intent_M1` are the CI95 half-widths of **(B1r minus cell B1)** on the same 1,080
rows at the same interval level. They are outputs of this cell: no value for either appears anywhere
in the registration, and neither was chosen after the fact.

| Metric | B1 | B1r | Delta | Speaker CI95 | **CI95 half-width** |
| --- | ---: | ---: | ---: | --- | ---: |
| Official pooled SLU-F1 | 61.14 | 62.23 | +1.09 | [-0.10, +2.37] | **h_SLU_M1 = 1.2350** |
| Intent (scenario+action) | 80.19 | 80.09 | -0.09 | [-1.31, +1.13] | **h_intent_M1 = 1.2212** |
| Scenario | 86.39 | 86.85 | +0.46 | [-0.58, +1.51] | 1.0433 |
| Action | 81.39 | 81.02 | -0.37 | [-1.54, +0.78] | 1.1570 |
| Pooled span F1 | 48.43 | 49.92 | +1.49 | [-0.29, +3.30] | 1.7947 |
| Exact slot F1 (row mean) | 31.35 | 32.46 | +1.11 | [-0.20, +2.46] | 1.3324 |
| SLU-F1 (row mean) | 40.15 | 41.36 | +1.21 | [+0.16, +2.34] | 1.0892 |

Saves / harms / ties on the own null: intent 28 / 29 / 1,023 (p = 1.000); scenario 23 / 18 / 1,039
(p = 0.533); action 26 / 30 / 1,024 (p = 0.689); exact slot F1 47 / 34 / 999 (p = 0.182); row SLU-F1
65 / 64 / 951 (p = 1.000). Equal-scenario: pooled SLU +1.54, intent -0.09.

Beside the two half-widths this cell replaces:

| Own null | h_SLU | h_intent | measured on |
| --- | ---: | ---: | --- |
| **M1, this cell (B1r - B1)** | **1.2350** | **1.2212** | the exemplar-supplied five-contact configuration, TRAIN A, np4, per-role rendering |
| B0r (review-off), which cell B1 had to borrow | 1.1218 | 1.0051 | a two-contact review-off configuration of the same harness |
| B4b-rep (slot store v2) | 1.3222 | 1.0682 | the slot-store-v2 five-contact configuration |

Ratios: h_SLU_M1 is **1.10x** the borrowed review-off figure and **0.93x** B4b-rep's; h_intent_M1 is
**1.22x** the borrowed figure and **1.14x** B4b-rep's. **The borrowed intent margin was too narrow
for this configuration by about a fifth.** Read plainly: every contrast that has been judged against
-1.0051 pp of intent on an exemplar-supplied arm -- cell B5e's included -- was judged against a
margin 0.22 pp tighter than the configuration's own noise, and owner decision 38 now directs those
contrasts to **1.2350 / 1.2212**.

Two consequences follow immediately and are recorded, not acted on here:

- **cell B5e's margin misfire is now quantified.** Its registered HARMFUL trigger fired because the
  intent CI95 lower bound of (B5e minus B1), **-1.5136**, crossed the borrowed **-1.0051** while the
  point estimate was -0.09 on 26 saves against 27 harms. Against this configuration's own margin,
  **-1.2212**, that lower bound still crosses -- by 0.29 pp instead of 0.51 pp. So the correct margin
  shrinks the misfire without erasing it, and the addendum of 2026-09-18 was right for the reason it
  gave: a contrast between two *different* configurations is wider by construction than any
  request-identical null, however correctly that null is measured. The B5e status stays what owner
  decision 25 made it -- NEUTRAL, non-inferiority not proven at the request-identical margin -- and
  nothing here re-decides it.
- **nothing in this cell licenses importing 1.2350 / 1.2212 anywhere else.** They are this
  configuration's, this roster's and this geometry's.

## The rule, applied unchanged

| Clause | Requirement | Value | Threshold | Passes |
| --- | --- | ---: | ---: | --- |
| 1(a), pooled SLU gain vs the anchor | CI95 lower bound of (B1r - anchor) > 0 | **+11.6386** | 0 | **YES** |
| 1(b), intent non-inferiority | CI95 lower bound > -1.0051 | **+0.8064** | -1.0051 | **YES** |
| 1(c), projection-v3 sign agreement | v3 pooled SLU delta agrees in sign with the unprojected | +11.9751 vs +13.6987 | same sign | **YES** |
| 2, the own null | CI95 half-widths of (B1r - B1); OUTPUTS | 1.2350 / 1.2212 | -- | reported |
| 4 (diagnostic), scenario band | no scenario's paired intent delta has a CI95 upper bound below zero | 0 of 18 breaching on both contrasts | -- | reported |
| 5, symmetric scorer | TRAIN sibling reported beside every official number | +12.2610 vs +13.6987 | -- | reported |

None of cell B1's three HARMFUL triggers fires: the pooled SLU CI95 lower bound is +11.64, far above
-1.1218; the intent CI95 lower bound is +0.81, above -1.0051 and above this cell's own -1.2212; and
no scenario breaches the band. **Clause 1 is cell B1's own rule** -- the three conjuncts, the
-1.0051 margin, the estimator, the draws and the seed are copied from the first pass's
preregistration section 7. It deliberately does **not** restate cell B1's twin clause: owner decision
37 asked for a request-identical replicate, no derangement twin is re-flown, and cell B1's twin
decomposition is quoted below, not re-measured.

## The twin decomposition, quoted and not re-measured

`docs/results/2026-09-18-slurp-b1-twin-verdict.md` established, on the same roster: arm minus twin
**+7.83 pp [+5.85, +9.75]** on pooled SLU; twin minus anchor **+4.77 pp [+3.20, +6.36]** with **nil
intent** (+0.19 [-1.03, +1.39]); so twenty *unrelated* real annotated exemplars buy **37.8 %** of the
first pass's gain and the row's own speech key buys the remaining **62.2 %**. This cell says nothing
about that split and does not revise it. No twin claim is made here.

## Request identity: the registered diagnostic

The **first model-facing request of every row is byte-identical to cell B1's** on the same sample id,
on **1,080 of 1,080 rows**, with zero differing rows. "Model-facing" is the whole request payload
minus exactly three named bookkeeping fields -- `request_id` (the flight counter), every
`evidence_provenance` entry's `relpath` (`rails-message/flight-<n>/<k>`, the same counter; each
entry's `lock_key` and `sha256` stay compared) and `decoding_params.id_slot` (which of the four
llama-server KV slots the scheduler handed the contact). `history`, `task_instruction`,
`supplied_evidence`, `tool_schemas`, `max_tokens`, `response_format`, `parallel_tool_calls`, `seed`,
`temperature`, `tool_choice`, `speech_feature_parts`, `speech_packet_sha256`, `speech_ref`,
`media_relpath`, `key_representation_id`, `matcher_policy_id`, `query_source`, `mmproj_loaded`,
`sample_rate_hz` and `audio_seconds` are all **inside** the compared digest. This is the B7a v2
read's own exclusion list, unchanged.

| Quantity | Value |
| --- | ---: |
| rows | 1,080 |
| FIRST model-facing request byte-identical to cell B1's | **1,080 of 1,080** |
| ... and the claim holds on every row | **yes**, 0 differences |
| FIRST whole-payload digest identical (carries the three bookkeeping fields) | 12 |
| Perception prompt tokens, summed over the flight | **3,884,813 on both arms, exactly** |
| FIRST response text identical | 244 of 1,080 |
| Solver first request byte-identical | **0 of 1,080** |
| ... identical once `history` is removed | 763 of 1,080 |
| Solver `train-exemplars` evidence-id list identical | **1,080 of 1,080** |
| Solver whole supplied-evidence-id list identical | 763 of 1,080 |
| rows byte-identical over the WHOLE trajectory | 24 |
| rows with different contact counts | 16 |

Read this honestly. The first request is identical everywhere, which is the claim the registration
made and the only one it could make; the first **response** is identical on 244 rows and differs on
836, which is exactly the factor this cell exists to measure -- greedy decoding at temperature 0 is
not bitwise reproducible across batch compositions. Every downstream request carries the upstream
answer in `history`, so no Solver request can be identical on a row whose Perception answer moved;
**removing `history` alone restores identity on 763 rows**, and the remaining 317 differ because the
Solver's supply also carries the *content-conditioned* `intent-boundaries` values, which are selected
from the Perception answer. The **prepared** part of the supply is unmoved: the twenty
`train-exemplars` value ids match **in order on 1,080 of 1,080 rows** on both instruments (the
request's own evidence-id list and each flight's sealed `agent-loop/supply` record), over the same
4,990 distinct values of the 9,354-facet pool, and the rendered exemplar volume is identical to the
character (mean 1,874.45, p50 1,807, p95 2,696, max 3,232). Against the anchor, for contrast, **zero**
of 1,080 first requests are identical -- that is what a real configuration difference looks like.

## Row agreement between the two passes

| Quantity | B1r vs B1 | B1r vs anchor | B1 vs anchor |
| --- | ---: | ---: | ---: |
| identical delivered text | **803 (74.35 %)** | 514 (47.59 %) | 519 (48.06 %) |
| identical delivered intent pair | **1,000 (92.59 %)** | 983 (91.02 %) | 989 (91.57 %) |
| delivered (scenario, action) pair differs | **80** | 97 | 91 |
| identical delivered entity set | **864 (80.00 %)** | 589 (54.54 %) | 595 (55.09 %) |

74.35 % byte-identical deliveries is close to the M4b replicate's 73.33 % (792 of 1,080) on the same
roster and geometry, which is the only other measurement of this quantity the program has. Every
arm's recomputed delivered-text digest equals its own sealed `response_text_sha256` on 1,080 of 1,080
rows.

## Delivery shape and dispositions

| Signal | B1r | B1 | anchor |
| --- | ---: | ---: | ---: |
| Solver completions **tool-call-shaped as text** | **0 of 1,092** | 0 of 1,087 | 0 of 1,085 |
| Solver completions that do not load as JSON | 2 of 1,092 | 4 of 1,087 | 7 of 1,085 |
| Reviewer completions tool-call-shaped as text | 1 of 2,180 | 1 of 2,171 | 0 of 2,167 |
| Perception completions that load as JSON | 1,080 of 1,080 | 1,080 of 1,080 | 1,080 of 1,080 |
| rows the official scorer could not parse | **2** | 4 | 7 |
| delivered answers starting with `{` | 1,080 | 1,080 | 1,080 |
| delivered answers carrying a tool-call marker | 0 | 0 | 0 |
| contacts-per-row histogram | 4:3, **5:1,065**, 8:2, 9:10 | 4:2, 5:1,071, 8:1, 9:6 | 4:3, 5:1,072, 9:5 |
| Reviewer contacts-per-row histogram | 1:2, 2:1,066, 3:2, 4:10 | 1:2, 2:1,071, 3:1, 4:6 | 1:3, 2:1,072, 4:5 |

**No delivery-shape failure of the EFF-1 kind is present.** EFF-1's signature was 145 of 1,092 Solver
completions returning a `<tool_call>`-shaped string and 137 rows the scorer could not parse; here the
Solver emits none, and the two unparseable rows are 2 of 1,080 against the anchor's own 7. One row,
`slurp:train:001642:audio--1504198588`, became unparseable against cell B1 and three
(`slurp:train:002081`, `slurp:train:003499`, `slurp:train:015927`) became parseable, a net of +2
parsed rows.

**One finite-completion row, and the harness declaration earned its keep.** Cell B1r carries
`native_episode.finite_completion_policy = "deliver-latest-or-abstain"` (item E13), the one declared
key cell B1 did not have. On **one** row -- `slurp:train:012249:audio-1501687677`, `reviewer` role,
`review` stage, `finish_reason` `length`, `revision_count` 0, `planner_accepted` false -- the frozen
core ended a Reviewer completion before authoritative delivery. The policy retained the row and
delivered the latest Solver draft (54 characters); the official scorer parsed it, and it is scored
like every other row. Nothing was filtered. **Without that key the flight would have aborted**, which
is precisely how cell B7a lost an arm on 2026-09-19. `planner_action_illegal`: **0** rows, on all
three arms. Cell B1 and the anchor each carry a single non-finite terminal disposition instead --
`revision_limit` on one row each (`slurp:train:006066` and `slurp:train:015846`).

**Correction to the sealed ledger row and to the closure note.** The exposure-ledger closure for this
run states "No finite-completion disposition on any row", and the spawn brief repeated it. The sealed
`phases.json` carries exactly **one** `terminal_disposition`, and its reason is `finite_completion`.
The mis-statement is understandable -- no receipt surfaces the count: `flight-receipts.json` and the
generation manifest contain no `finite_completion` field at all, and the only place the disposition
exists is the phase artefact. This read does not edit the ledger; the coordinator owns that row, and
`docs/receipts/slurp-finite-completion-exposure-v1.json` (which proves zero finite completions on the
*sealed comparator* arms, and is therefore still correct about them) should gain this arm's one.

## Review loop and the M1 instrument

| Quantity | B1r | B1 | anchor | cell B1's verdict |
| --- | ---: | ---: | ---: | ---: |
| Planner `REVISE` tokens emitted | **12** | 8 | **6** | 7 rows (B1) / 5 rows (anchor) |
| rows with a Planner `REVISE` token | 12 | 7 | 5 | 7 / 5 |
| revisions executed (rows with a second Solver visit) | **12** | 7 | 5 | 7 / 5 |
| rows whose intent changed across the revision | 11 | 3 | 2 | 3 / 2 |
| exemplar acquire transitions per row | exactly 1 on 1,080 / 1,080 | exactly 1 on 1,080 / 1,080 | n/a | exactly 1 |
| native task-contract tool calls (all from `reviewer`) | 1,088 | 1,084 | 1,082 | 1,084 / 1,082 |

The instrument reproduces cell B1's own verdict readings exactly where they measure the same thing
(7 / 7 / 3 on the arm and 5 / 2 on the anchor), which is what licenses reading B1r's beside them. The
anchor's **6** `REVISE` tokens over **5** rows is the arithmetic behind the two different numbers the
program has quoted for the anchor's revisions: one row's second `REVISE` was refused by the revision
limit and sealed as a `revision_limit` terminal disposition. B1r takes the revise route on 12 rows
against cell B1's 7 -- a batch-composition difference of 5 rows in 1,080, not a mechanism change; the
role graph, the revision cap and the Planner instruction are byte-identical. Eleven of B1r's twelve
revisions changed the delivered intent against cell B1's three of seven; on twelve rows that is a
count, not a rate, and it is recorded rather than attributed.

| M1 diagnostic | B1r | B1 | anchor | cell B1's verdict |
| --- | ---: | ---: | ---: | ---: |
| gold intent among the arm's own Perception candidates | 942 | 939 | 937 | 939 / 937 |
| delivered intent among the arm's own candidates | 1,038 | 1,044 | 1,051 | 1,044 / 1,051 |
| delivered intent correct | 865 | 866 | 842 | 866 / 842 |
| escape to a neighbour intent | **8 rows (0.74 %)**, 7 onto gold | 6 (0.56 %), 5 onto gold | -- | 6 / 5 |
| delivered outside candidates and exemplars | 34 | 30 | -- | 30 |
| A2 recovery set (113 rows) converted | **12** | 10 | 0 | 10 / 0 |
| delivered mentions echoing a supplied exemplar filler | 498 of 1,002 (**0.497**) | 500 of 1,000 (0.500) | 265 of 910 (**0.291**) | 0.500 / 0.291 |
| gold-exact mentions | **515** | 501 | 340 | 501 / 340 |

Every one of cell B1's published M1 readings reproduces; the replicate's own values sit beside them
within a handful of rows. The exemplar-filler echo -- the convention-transfer signal that carried the
first pass's explanation -- reproduces at **0.497 against 0.500**, against the anchor's 0.291 base
rate, on a supply that is provably the same twenty values per row.

## Every scenario (natural mixture; equal-scenario mean in the last row)

### B1r minus the sealed anchor

| Scenario | n | Anchor SLU | B1r SLU | Delta | Anchor intent | B1r intent | Delta | Intent CI95 | Net harmed | Flag | Beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 52.66 | 68.67 | +16.01 | 83.33 | 86.67 | +3.33 | [-4.65, +14.58] | -2 | no | no |
| audio | 60 | 47.75 | 63.05 | +15.30 | 76.67 | 81.67 | +5.00 | [+0.00, +12.90] | -3 | no | no |
| calendar | 60 | 48.38 | 65.06 | +16.68 | 75.00 | 80.00 | +5.00 | [+0.00, +11.48] | -3 | no | no |
| cooking | 60 | 62.47 | 65.44 | +2.97 | 85.00 | 88.33 | +3.33 | [+0.00, +8.93] | -2 | no | no |
| datetime | 60 | 59.52 | 69.75 | +10.23 | 83.33 | 91.67 | +8.33 | [+1.96, +14.55] | -5 | no | no |
| email | 60 | 36.64 | 56.53 | +19.90 | 85.00 | 86.67 | +1.67 | [+0.00, +5.66] | -1 | no | no |
| general | 60 | 15.45 | 31.37 | +15.92 | 36.67 | 36.67 | +0.00 | [-10.20, +8.70] | +0 | no | no |
| iot | 60 | 55.53 | 68.76 | +13.23 | 86.67 | 86.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| lists | 60 | 43.55 | 53.79 | +10.24 | 83.33 | 83.33 | +0.00 | [-4.55, +4.92] | +0 | no | no |
| music | 60 | 34.53 | 47.67 | +13.14 | 76.67 | 80.00 | +3.33 | [+0.00, +8.62] | -2 | no | no |
| news | 60 | 44.24 | 62.57 | +18.33 | 80.00 | 80.00 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| play | 60 | 46.82 | 52.94 | +6.11 | 58.33 | 51.67 | -6.67 | [-19.61, +6.67] | +4 | no | no |
| qa | 60 | 57.04 | 60.98 | +3.94 | 75.00 | 80.00 | +5.00 | [+0.00, +11.32] | -3 | no | no |
| recommendation | 60 | 49.75 | 67.78 | +18.04 | 90.00 | 91.67 | +1.67 | [-3.64, +7.14] | -1 | no | no |
| social | 60 | 34.74 | 58.89 | +24.15 | 66.67 | 75.00 | +8.33 | [+1.75, +15.79] | -5 | no | no |
| takeaway | 60 | 48.84 | 56.12 | +7.28 | 85.00 | 81.67 | -3.33 | [-7.69, +0.00] | +2 | no | no |
| transport | 60 | 51.34 | 62.75 | +11.41 | 86.67 | 86.67 | +0.00 | [+0.00, +0.00] | +0 | no | no |
| weather | 60 | 53.81 | 77.01 | +23.20 | 90.00 | 93.33 | +3.33 | [+0.00, +8.62] | -2 | no | no |
| **equal-scenario mean** | 18 | | | **+13.67** | | | **+2.13** | | | | |

**All eighteen scenarios gain on pooled SLU against the anchor; none loses.** `social` **+24.15**,
`weather` +23.20 and `email` +19.90 lead; `cooking` **+2.97**, `qa` +3.94 and `play` +6.11 trail --
the same shape the first pass recorded, with `qa` and `cooking` again the two weakest. On intent no
scenario breaches the band (0 of 18 with a CI95 upper bound below zero) and owner decision 17's
net-harmed diagnostic fires on **no scenario**: the worst net figure is `play` at +4.

### B1r minus cell B1 (the own null)

| Scenario | n | B1 SLU | B1r SLU | Delta | B1 intent | B1r intent | Delta | Intent CI95 | Net harmed | Flag | Beyond band |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | --- |
| alarm | 60 | 65.28 | 68.67 | +3.40 | 81.67 | 86.67 | +5.00 | [+0.00, +10.45] | -3 | no | no |
| audio | 60 | 60.35 | 63.05 | +2.70 | 78.33 | 81.67 | +3.33 | [+0.00, +12.90] | -2 | no | no |
| calendar | 60 | 64.16 | 65.06 | +0.89 | 78.33 | 80.00 | +1.67 | [-3.64, +7.84] | -1 | no | no |
| cooking | 60 | 64.74 | 65.44 | +0.71 | 88.33 | 88.33 | +0.00 | [-4.84, +5.08] | +0 | no | no |
| datetime | 60 | 69.80 | 69.75 | -0.06 | 88.33 | 91.67 | +3.33 | [+0.00, +7.94] | -2 | no | no |
| email | 60 | 57.93 | 56.53 | -1.40 | 83.33 | 86.67 | +3.33 | [+0.00, +8.06] | -2 | no | no |
| general | 60 | 20.41 | 31.37 | +10.96 | 43.33 | 36.67 | -6.67 | [-15.87, +1.96] | +4 | no | no |
| iot | 60 | 64.30 | 68.76 | +4.46 | 88.33 | 86.67 | -1.67 | [-5.36, +0.00] | +1 | no | no |
| lists | 60 | 53.45 | 53.79 | +0.34 | 85.00 | 83.33 | -1.67 | [-7.46, +3.64] | +1 | no | no |
| music | 60 | 48.87 | 47.67 | -1.19 | 78.33 | 80.00 | +1.67 | [+0.00, +5.56] | -1 | no | no |
| news | 60 | 60.85 | 62.57 | +1.72 | 83.33 | 80.00 | -3.33 | [-9.09, +0.00] | +2 | no | no |
| play | 60 | 49.94 | 52.94 | +3.00 | 60.00 | 51.67 | -8.33 | [-20.00, +1.79] | +5 | FLAG | no |
| qa | 60 | 58.16 | 60.98 | +2.82 | 75.00 | 80.00 | +5.00 | [+0.00, +11.32] | -3 | no | no |
| recommendation | 60 | 68.67 | 67.78 | -0.89 | 90.00 | 91.67 | +1.67 | [-3.70, +7.27] | -1 | no | no |
| social | 60 | 57.33 | 58.89 | +1.56 | 75.00 | 75.00 | +0.00 | [-4.76, +4.92] | +0 | no | no |
| takeaway | 60 | 60.43 | 56.12 | -4.31 | 85.00 | 81.67 | -3.33 | [-7.69, +0.00] | +2 | no | no |
| transport | 60 | 62.79 | 62.75 | -0.04 | 90.00 | 86.67 | -3.33 | [-7.35, +0.00] | +2 | no | no |
| weather | 60 | 73.93 | 77.01 | +3.08 | 91.67 | 93.33 | +1.67 | [+0.00, +5.41] | -1 | no | no |
| **equal-scenario mean** | 18 | | | **+1.54** | | | **-0.09** | | | | |

No scenario breaches the band here either, but owner decision 17's diagnostic **fires on one**:
`play`, net +5 harmed rows on intent (delta -8.33, CI95 [-20.00, +1.79]). That is the flag doing its
job on a contrast in which nothing changed but batch composition -- it is the size of stratum noise
at 60 rows, and it is the clearest available warning against reading a single 60-row scenario as
evidence of anything.

## Projection v3 and the TRAIN symmetric view, beside the rule

Owner decision 7 of 2026-09-17 makes `slurp-slu-official-projected-v3-train` the fixed
post-processing of every official number, and owner decision 23 keeps the decision number
OFFICIAL and UNPROJECTED; v3 enters this rule only through clause 1(c), the
sign-agreement conjunct fixed before contact. Each arm's sealed `outputs.jsonl` was
COPIED under the analysis directory and the registered scorer read the copy; the sealed
bytes were never opened for writing.

| Arm | v3 SLU | v3 intent | v3 scenario | v3 action | v3 span F1 | Labels / fillers changed |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| anchor | 51.99 | 79.35 | 85.46 | 80.65 | 40.30 | 20 / 195 |
| B1 | 62.67 | 81.76 | 87.13 | 82.96 | 52.65 | 24 / 90 |
| **B1r** | 63.97 | 82.31 | 87.50 | 83.24 | 54.25 | 30 / 87 |
| direct | 34.31 | 75.37 | 84.17 | 75.93 | 23.24 | 47 / 36 |

v3 contrasts: **B1r - anchor SLU +11.98 [+9.87, +14.05]**, intent +2.96 [+1.90, +4.11], span F1 +13.94 [+11.32, +16.52]; B1r - B1 SLU +1.30 [+0.01, +2.67]; B1r - direct SLU +29.66 [+26.21, +33.12]. The recomputed B1 - anchor v3 delta is +10.67 [+8.55, +12.77], reproducing the first pass's published +10.67, and
the anchor, cell B1 and the direct anchor all reproduce their registered v3 aggregates
exactly -- which is what licenses reading the replicate's v3 number beside them.
**Clause 1(c) passes: the unprojected delta is +13.70 pp and the v3 delta
is +11.98 pp, the same sign.**

Owner decision 14 of 2026-09-17 registered the TRAIN sibling
`slurp-slu-f1-normalized-v1-train`; it is reported beside every official number and is
never a gate here (clause 5).

| Arm | Official pooled SLU | Symmetric pooled SLU | Delta | Official span F1 | Symmetric span F1 | False merges |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| anchor | 48.53 | 52.09 | +3.56 | 29.50 | 41.38 | 34 |
| B1 | 61.14 | 62.97 | +1.83 | 48.43 | 54.51 | 34 |
| **B1r** | 62.23 | 64.35 | +2.12 | 49.92 | 56.00 | 34 |
| direct | 33.89 | 34.46 | +0.57 | 21.10 | 24.38 | 34 |

Symmetric contrasts: **B1r - anchor SLU +12.26 [+10.14, +14.37]**, intent +2.13 [+0.81, +3.38]; B1r - B1 SLU +1.38 [+0.06, +2.77]; the recomputed B1 - anchor symmetric delta is +10.89 [+8.72, +13.00], reproducing the first pass's
published +10.89. The anchor's and the direct anchor's symmetric readings reproduce the
registered 52.09 / 41.38 and 34.46 / 24.38 exactly. The sign agrees with the official
reading on every contrast, so clause 5 is satisfied as reported.

## Entity mass, by type

The official scorer's own matching, reconstructed from each arm's sealed outputs; every row's
reconstruction was checked against that row's sealed official `slu_f1` word and character counts
before any table was built, and the per-type decomposition sums to each arm's official aggregate
(max abs diff 6.8e-13, and **exactly 0** on B1r).

| Roster total, all 53 types | Anchor | B1 | B1r |
| --- | ---: | ---: | ---: |
| gold mentions (fixed) | 941 | 941 | 941 |
| predicted mentions | 910 | 1,000 | **1,002** |
| exact mentions | 272 | 470 | **485** |
| different-filler mentions | 276 | 205 | 206 |
| omitted mentions | 393 | 266 | **250** |
| spurious mentions | 362 | 325 | **311** |
| filler-distance (surface) mass | 407.23 | 267.07 | 277.71 |

The anchor -> B1 column reproduces cell B1's verdict exactly (272 -> 470 exact, 393 -> 266 omitted,
362 -> 325 spurious, 910 -> 1,000 predicted). One definitional note: the first verdict quoted the
filler-distance mass as 814.46 -> 534.14, which is the same quantity counted on **both** the
false-positive and the false-negative side; this table counts it once, and 407.23 / 267.07 are
exactly half of those figures.

B1r removes more false-negative mass than B1 on the types the exemplars reach -- `time` 68.07 ->
60.60, `place_name` 71.36 -> 65.56, `date` 129.35 -> 123.85, `media_type` 46.50 -> 41.60,
`transport_type` 35.50 -> 29.50, `weather_descriptor` 21.57 -> 14.57 -- and gives some back on
`food_type` (29.34 -> 36.06), `event_name` (32.83 -> 37.49) and `order_type` (34.95 -> 39.13). None
of that is attributed: it is one realisation's noise on a supply that did not move.

## Cost and duty cycle

| Figure | B1r | B1 | Anchor | Direct | Registered ceiling |
| --- | ---: | ---: | ---: | ---: | ---: |
| Generation contacts (per row) | **5,443 (5.040)** | 5,425 (5.023) | 5,417 (5.016) | 1,080 (1.000) | 11,880 (11) |
| Repeated speech seconds | **15,542.42** | 15,494.60 | 15,459.76 | 3,084.53 | 33,930 |
| Prompt / completion tokens | **49,678,439 / 257,424** | 49,388,949 / 255,524 | 45,998,267 / 255,153 | 2,459,915 / 26,764 | -- |
| Prompt tokens per contact | 9,127.0 | 9,104.0 | 8,491.8 | 2,277.7 | -- |
| Native task-contract tool calls | **1,088** | 1,084 | 1,082 | 0 | 6,480 |
| FIT receipts / endpoints | **5,443 / 21,772** | 5,425 / 21,700 | 5,417 / 21,668 | -- | -- / 47,520 |
| GPU hours (monitor active seconds) | **3.8507 (13,862.65 s)** | 3.6819 (13,254.97 s) | 3.3880 (12,196.65 s) | 0.0871 | 12.0 |
| Generation wall seconds | 14,437.7 | 13,894.2 | not in its receipts | 450.6 | -- |
| Slot occupancy; utilisation; parked | 0.868; 87.09 %; 0.039 | 0.877; 91.01 %; 0.045 | --; 88.73 %; 0.022 | 0.658; 55.66 %; 0.281 | -- |
| Mean latency (s); preprocess (s, workers) | 9.213; 14.01 at 8 | 8.982; 10.01 at 8 | -- | 1.098; 13.03 at 8 | -- |
| Official scoring jobs (seconds) | 1 (167.70) | 1 (166.22) | -- | -- | 1 |

Every registered ceiling held with room: **45.8 %** of the contact ceiling (headroom 6,437 calls),
45.8 % of the speech ceiling, **32.1 %** of the GPU-hour ceiling, 45.8 % of the FIT-endpoint ceiling
and 16.8 % of the task-contract ceiling. Run-cumulative over the single attempt of this run id:
5,443 calls and 15,542.42 repeated speech seconds. Against the first pass the replicate costs
**+18 contacts (+0.33 %), +47.82 speech seconds, +289,490 prompt tokens (+0.59 %), +1,900 completion
tokens, +4 tool calls, +0.169 GPU hours and +543.6 s of wall clock** -- the difference between two
realisations of the same bytes, driven mostly by the five extra revise routes.

Per-role prompt volume, which is where a replicate's cost has to be invisible if it really is one:

| Role | B1r contacts | B1 contacts | B1r median prompt tokens | B1 median | Delta | B1r p90 | B1 p90 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| perception | 1,080 | 1,080 | 3,593 | 3,593 | **0** | 3,650.1 | 3,650.1 |
| solver | 1,092 | 1,087 | 9,769 | 9,762 | +7 | 11,586.4 | 11,514.0 |
| reviewer | 2,180 | 2,171 | 10,672 | 10,655 | +17 | 12,926.1 | 12,867.0 |
| planner | 1,091 | 1,087 | 11,649 | 11,598 | +51 | 13,450.0 | 13,397.4 |

The Perception median, p90 **and flight total (3,884,813 tokens on both arms)** are identical to the
token, which is the arithmetic consequence of 1,080 byte-identical first requests. The downstream
medians move by 7 to 51 tokens -- the length of a differently-worded upstream answer carried in
`history`, not a prompt change.

**Prompt fit.** `every_request_fits = true` on all 5,443 receipts; the minimum margin is **8,254
tokens** in the `planner` phase against the 24,576-token slot (cell B1: 8,600 in `reviewer`), and the
widest realized request needed **16,322** tokens (cell B1: 15,976). Per phase: perception 20,306
margin / 4,270 widest; solver 10,166 / 14,410; reviewer 8,276 / 16,300; planner 8,254 / 16,322.

**Throughput, from the serving session's own `server.log` release records** -- never from
`monitor.jsonl` `requests_total`, which undercounts (its `requests_delta` for this window reads
4,294 against 5,443 realized contacts). The log was opened read-only; the resident process was never
touched. **5,443 release records fall inside this flight's sealed contact window, exactly matching
the 5,443 client contacts**, and the join is a measurement rather than an estimate: `n_tokens` at
release minus generated plus one equals the client's `usage.prompt_tokens` on **5,443 of 5,443**
contacts (100.00 %), balanced across the four KV slots (1,378 / 1,389 / 1,340 / 1,336).

| Throughput figure | Value |
| --- | ---: |
| contacts per minute, release records over the measured span (14,139.6 s) | **23.10** |
| contacts per minute over the sealed generation wall (14,437.7 s) | 22.62 |
| contacts per minute, cell B1 for comparison | 23.43 |
| prefilled tokens total / per row | 28,157,676 / 26,071.9 |
| server-side prompt tokens total | 49,678,439 |
| prefix-cache hit share | 43.32 % |
| aggregate prefill tokens per second | 1,950.3 |
| truncations | 0 |

Per role, prefilled tokens and cached share: perception 1,477,230 (61.97 % cached), solver 6,657,524
(36.05 %), reviewer 10,017,656 (56.36 %), planner 10,005,266 (19.49 %).

## Ledger closure inputs (the coordinator edits the ledger; this read does not)

- contacts **5,443**; repeated speech seconds **15,542.422562500085**; native task-contract tool
  calls **1,088**; request-fit receipts **5,443** / FIT endpoints **21,772**; GPU hours **3.8507**
  (13,862.650144 monitor active seconds); prompt tokens **49,678,439**; completion tokens
  **257,424**; wall **14,437.740793 s**; slot occupancy **0.8683**; utilisation **87.09 %**; parked
  **0.0388**; one official scoring job, **167.70 s**.
- **one** `finite_completion` terminal disposition (`slurp:train:012249:audio-1501687677`), retained
  and scored -- the closure note's "No finite-completion disposition on any row" is incorrect.
- zero `planner_action_illegal` rows; zero aborts; zero recovery re-registrations.

## The harness-admission consequence

**Clause 3, on REPLICATED: module M1's provisional obligation is MET.** The entry
`docs/receipts/harness-admission.json`, row
`SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-TRAIN-FOLD-A-RECOVERY-V2`, whose `provisional.requirement`
names exactly this form ("a request-identical replicate of this cell (about 3.7 GPU hours); a second
entry records the replication and this entry stays"), is discharged. The coordinator owns the
receipt; `scripts/checks/harness_admission_check.py` is the oracle. This verdict writes no row and
edits no receipt. The change it supports, in the two-part form the M4b pair used on 2026-09-19:

1. **The first entry stays** and its `provisional` block is flipped:
   - `state`: `MET`
   - `discharged_by`: `SAEA-SLURP-NATIVE-EXEMPLARS-K20-ANCHOR-REPLICATE-V1`
     (`attempt-slurp-native-exemplars-k20-anchor-replicate-train-fold-a-generation-v1`), 2026-09-19,
     `docs/results/2026-09-19-slurp-b1-replicate-verdict.md`
   - `note`: the replication obligation is discharged; the effect may be cited as replicated and the
     SLURP default plan may carry the `train-exemplars` store
   - `supersedes`: the existing `UNMET` block, verbatim.
2. **A second entry records the replication**, keyed on the replicate run id, with:
   - **module**: the same speech-keyed exemplar supply to the Solver
     (`knowledge_stores.train-exemplars`), **PER-ROLE tool-schema rendering** (item E17 not armed)
   - **class / key / on / off**: unchanged from the first entry -- release
     `171aa4a82c2b15fff2c72e907ea80298be8d72309cca0d7367eb50debb042129`, snapshot
     `4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9`, `phase_supply.solver` at
     k = 20 with `saea-fuse-supplyfilter-v1` (m = c = top_l = 20),
     `saea-rank-wcos-prior-agree-v1` (w_cos = 1, w_prior = 0, w_agree = 0), tau 0.0,
     `store_role` `train-exemplars`; OFF is the store's absence, the `stores` class's own null
   - **status**: `ADMITTED`, replication **MET**
   - **primary**: official pooled SLU-F1, 1,080 paired TRAIN A rows, 125 speaker clusters, 10,000
     draws, seed 20260915: 48.53 -> 62.23, **+13.70 pp CI95 [+11.64, +15.73]**, equal-scenario
     +13.67; row SLU-F1 saves / harms 273 / 57 (McNemar p 6.0e-35)
   - **guards**: intent 77.96 -> 80.09, **+2.13 pp CI95 [+0.81, +3.38]** against the -1.0051 margin:
     passes; scenario +2.04, action +1.76; 0 of 18 scenarios breach the intent band; owner decision
     17's net-harmed diagnostic fires on no scenario of the gating contrast
   - **margins_from**: **this run itself** -- the own null (B1r minus B1) measured on this roster and
     geometry, **h_SLU 1.2350 pp and h_intent 1.2212 pp at CI95**, which owner decision 38 makes the
     margin regime for every later contrast involving an exemplar-supplied arm
   - **cost**: 5,443 contacts (5.040 per row), 15,542.42 repeated speech seconds, 1,088 task-contract
     tool calls, 3.8507 GPU hours, wall 14,437.7 s, slot occupancy 0.868, utilisation 87.09 %, parked
     0.039, one finite-completion row retained
   - **not_admitted_for**: any test-split, Fold B or DEV-1000 claim; any claim about k, the fuse
     policy, the rank weights or the exemplar pool beyond the flown values; any claim that this
     cell's own null transfers to another configuration; any claim about constant tool-schema
     rendering, which this cell does not arm.
3. **The SLURP default plan may now carry the store.** `configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`
   gains the whole `knowledge_stores.train-exemplars` block the M1 entry's `switch.on` records, in
   the same change, and the plan's `modules` list gains the module. That is a coordinator action, not
   this read's.

## The margins every later B1-based comparator reads against (owner decision 38)

From here on, a contrast one of whose arms carries the exemplar supply reads against **h_SLU = 1.2350
pp** and **h_intent = 1.2212 pp**, not against cell B0r's 1.1218 / 1.0051 and not against cell
B4b-rep's 1.3222 / 1.0682. The values, their full measured set and their scope are sealed in
`own-null.json` under the analysis directory. Cells whose registrations quoted the borrowed figures
and whose arms are exemplar-supplied -- cell B5e, and any later cell built on the exemplar supply --
are affected; their point estimates do not change and their published verdicts are not re-decided
here. A cell whose arms are *not* exemplar-supplied keeps its own configuration's margins; owner
decision 38's rule is per configuration, not per carrier.

## What is not claimed

- **No superiority, generalization, paper-scale or held-out claim.** TRAIN Fold A is an exposed
  discovery roster and these are **development numbers** (owner decision 28); they are never compared
  with a published TEST baseline. Fold B, DEV-1000 and the test split stay untouched and unread.
- **Nothing is re-decided about cell B1.** This read does not enlarge, average, re-estimate or
  replace the first pass's numbers; the first verdict stands unchanged beside this one, and the two
  are two realisations, not one pooled estimate.
- **No twin claim**, and no revision of the presence/key attribution. The twin is quoted, not
  re-flown.
- **No claim about k, the fuse policy, the rank weights, the exemplar pool or the derangement seed**
  beyond the flown values; no sweep was run.
- **No geometry claim, and no claim about constant tool-schema rendering.** Cell B1r deliberately
  keeps **per-role** rendering (item E17 not armed), so every number here is a per-role number. If
  efficiency cell EFF-1's constant rendering ever enters the SLURP default plan, this cell's figures
  remain the per-role ones and a later cell must say so.
- **No claim that this cell's own null transfers to any other configuration.** h_SLU_M1 and
  h_intent_M1 belong to the exemplar-supplied five-contact configuration, this roster and this
  serving geometry.
- **No sub-population claim.** The per-scenario tables and the `play` decision-17 flag are reported
  diagnostics; no row was filtered from any number, including the finite-completion row.
- **Nothing about any in-flight cell**, and nothing about Earnings or Audio2Tool.
- **One replicate, not a family.** A third pass of this configuration would be repeat-to-pass and is
  neither registered nor authorized, whichever way clause 1 fell.

## Files

Analysis directory `SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-B1-REPLICATE-OWN-NULL-PAIRED-ANALYSIS-V1`,
written by this read; every input and output is hashed in its `README.md` and in
`score-contrasts.json`.

| File | SHA-256 |
| --- | --- |
| `score-contrasts.json` | `f82ddaf1689536fedc1c9ef0c66f00cda9f55bffa74b80bd99c0c82492a7f831` |
| `own-null.json` | `bfc88110be264223d5540ab0aef564b9598c64770db5b1bb3a35318eefc5f84c` |
| `per-scenario-tables.json` | `a78469a9fda26781530596de3b1584673d3ca348669ffc905fd5fd1650fced03` |
| `flight-diagnostics.json` | `ae68201f9d8e1c92b613ed84fe450d4f7635a19acedf819043a3bf9f71ff84a9` |
| `server-join.json` | `cf2528269652c46bf98d2bf3b7e0a036a224af2cf968bab1d91f9a4038d3cba8` |
| `slot-diagnostics.json` | `376d0e4fe96604c6b4f5b783f176860b8ea3642dc23f064cc8801a9ba761b2ab` |
| `README.md` | `6532af0e27ebcce9b09bc1a87f4bd06cfccc7eea597d89b62f4d64f7028e45ce` |
| `b1r_replicate_paired_read.py` | `979a5063ca7a42e5f1177f0bf464126c419be3246c1a2f368fb1c722658aaeef` |
| the model-free v3 and TRAIN symmetric score files, and the verified outputs copies | listed in `score-contrasts.json` under `outputs` |
