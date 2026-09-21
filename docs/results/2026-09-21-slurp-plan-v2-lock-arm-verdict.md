# NEUTRAL -- cell PLAN: the default plan flown as one arm on the tool-free B1-notool base, SLURP TRAIN Fold A, 1,080 rows

**The preregistered rule names ADMITTED / NEUTRAL / HARMFUL, and this read reaches NEUTRAL.** Both
gating guards are non-inferior at their own-null margins and neither shows a measured loss. The
primary guard -- official pooled SLU-F1 -- gains +1.5009 pp but its CI95 includes zero, so no gain is
proven; the intent guard gains +2.2222 pp with a CI95 that excludes zero. Under owner decision 25 the
SLU movement is recorded as beneficial-but-unproven, not as a gain. NEUTRAL is a licence to keep the
default plan in use; it is not evidence that any one module works.

Read 2026-09-21 by the implementer, model-free, from the sealed bytes of four flights. Status,
tables and every number below are the output of `plan_cell_read.py`
(`72952d20a22dbeea5e0f67e4343c25a3f74fbea28451fd39b938b36877443af3`), execution profile
`model-free-check`, analysis root
`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-DEFAULT-PLAN-LOCK-PAIRED-ANALYSIS-V1/`.

**Exposure.** Zero model, tokenizer, encoder, ASR, server, GPU, paid-API and network contacts. Every
scorer invocation is a registered model-free scoring over a **copy** of sealed bytes written under
this read's own output root. No sealed file was opened for writing, moved or renamed. No run
directory, exposure-ledger row, harness-admission receipt or results-ledger row was edited by this
read. No utterance text, transcript, gold filler or model output is printed here: counts, rates,
scenario names, percentages and content hashes only. Gold entered exactly where it always enters --
inside the registered scorer.

**Claim boundary.** Development numbers only (owner decision 28). Official SLURP `evaluate.py` at its
pinned commit `8eb16545762be97ace75334109d73824217311f1` on **TRAIN Fold A**, 1,080 rows, 18
scenarios of 60, 125 speaker clusters. TRAIN Fold A is an exposed discovery roster. Nothing here is a
test claim, a superiority claim, a generalisation claim, a component-causal claim, a cross-carrier
claim or a geometry claim, and nothing here is comparable with a published TEST baseline.

## 0. The lock statement

The PLAN arm's official numbers are the **candidate v2.0 lock numbers**:

| | official pooled SLU-F1 | intent accuracy |
| --- | ---: | ---: |
| **cell PLAN (candidate v2.0 lock)** | **63.6304** | **82.2222** |

Source: `score-contrasts.json` (`3e09c7aff96359f8a16c7e4f271443f103b39635459c4b4514b21d6a4c3397b7`),
`official_aggregates.arm`.

**This is a candidate, not the lock.** It becomes the v2.0 lock record only once the replicate arm
PLANr reads and the pair replicates; the provisional v2.0 lock record of 2026-09-20
(`docs/results/2026-09-20-slurp-v2-provisional-lock-v1.md`) stands until then. Section 10 states the
supersession condition. The bar of decision 1-26 (SLU >= 64 and intent >= 78) is met on intent
(82.2222) and missed on SLU by 0.3696 pp (63.6304 against 64).

## 1. Gating contrast, against the sealed tool-free base

Comparator: `SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1`, the sealed B1-notool arm. Margins are cell
B1r's own-null half-widths, `h_SLU = 1.235` and `h_intent = 1.2212`. Paired on the same 1,080 sample
ids; 10,000-replicate paired whole-speaker cluster bootstrap.

| guard | base | arm | delta pp | CI95 | CI90 | margin h | verdict |
| --- | ---: | ---: | ---: | --- | --- | ---: | --- |
| official pooled SLU-F1 | 62.1295 | 63.6304 | **+1.5009** | [-0.0422, +3.2440] | [+0.1750, +2.9377] | 1.235 | non-inferior; gain not proven |
| intent accuracy | 80.0000 | 82.2222 | **+2.2222** | [+0.9240, +3.5573] | [+1.1363, +3.3258] | 1.2212 | non-inferior; CI95 excludes zero |

Supporting per-row metrics (McNemar exact two-sided, saves / harms):

| metric | base | arm | delta pp | CI95 | saves | harms | p |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| action exact | 81.1111 | 83.5185 | +2.4074 | ±1.3212 | 41 | 15 | 0.0007 |
| intent (scenario+action) exact | 80.0000 | 82.2222 | +2.2222 | ±1.3166 | 40 | 16 | 0.0018 |
| scenario exact | 86.4815 | 87.3148 | +0.8333 | ±1.2262 | 26 | 17 | 0.2221 |
| slot-F1 exact | 31.5346 | 34.9935 | +3.4590 | ±1.6890 | 84 | 41 | 0.0002 |
| per-row SLU-F1 | 40.6869 | 42.2464 | +1.5595 | ±1.3524 | 117 | 65 | 0.0001 |
| pooled span-F1 micro | 49.0276 | 53.7755 | +4.7479 | ±2.5810 | -- | -- | -- |

The roster is balanced at 18 x 60, so the natural-mixture and equal-scenario weightings coincide: the
equal-scenario intent delta is +2.2222 pp, identical to the natural-mixture delta
(`per-scenario-tables.json` `19ad6034802c366df6fcfc39116493302904036c529c59cf626a38da9529330c`,
`natural_mixture_and_equal_scenario`). Row counts: arm 1,080 scored / 1,079 parsed / 1 malformed
retained; base 1,080 scored / 1,076 parsed / 4 malformed retained.

Source: `score-contrasts.json`
(`3e09c7aff96359f8a16c7e4f271443f103b39635459c4b4514b21d6a4c3397b7`), `decision.guards` and
`comparisons.arm_vs_comparator`.

## 2. Lock comparison (reported, never a gate)

Lock comparator: `SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1`
(cell B8a's B5e base), paired against the arm on the same 1,080 rows.

| lock side | lock SLU / intent | arm SLU / intent | SLU delta | CI95 | intent delta | CI95 |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| B5e official | 62.3351 / 80.0926 | 63.6304 / 82.2222 | +1.2954 | [-0.0786, +2.7645] | +2.1296 | [+1.0309, +3.3066] |
| B5e + normaliser node (the provisional lock) | 63.7757 / 81.8519 | 63.6304 / 82.2222 | **-0.1453** | [-1.4857, +1.2955] | **+0.3704** | [-0.6187, +1.3746] |

**Against the provisional lock as it is actually registered -- with the `saea-deliver-normalise-v3`
node applied -- the default plan is at parity on both metrics.** Both deltas sit well inside the
own-null margins (|-0.1453| << 1.235; |+0.3704| << 1.2212), and both CIs straddle zero.

**Integrity of the lock side.** The node-applied numbers were re-derived here model-free, by replaying
the registered normaliser over a byte-verified copy of the lock arm's sealed `outputs.jsonl`
(0 model calls, 1,080 rows) and scoring the replay ONCE with the official scorer. They reproduce the
registered B8a values exactly -- SLU 63.775710515453355 against registered 63.7757, intent
81.85185185185185 against registered 81.8519 -- and an independent projection-v3 scoring over the
untouched OFF copy returns byte-identical values (`reproduced: true`, `cross_check_agrees: true`).

Source: `lock-comparison.json` (`fa54e32deebcfc8df1470346ccd1fc52826b98fafbe740d1a628f1608e1a430c`),
`registered_reproduction` and `comparisons`.

## 3. The v3-scorer caveat -- what the SLU gain in section 1 actually is

The arm applies `saea-deliver-normalise-v3` in flight; the B1-notool base does not. Scoring both
sides under the same normalisation removes almost all of the SLU difference:

| scorer | base SLU | arm SLU | delta pp |
| --- | ---: | ---: | ---: |
| `slurp-slu-official-train` (official; arm normalised, base not) | 62.1295 | 63.6304 | +1.5009 |
| `slurp-slu-official-projected-v3-train` (both normalised) | 63.5973 | 63.6304 | **+0.0331** |
| `slurp-slu-f1-normalized-v1-train` (TRAIN symmetric) | 62.1295 | 63.6304 | +1.5009 |

The base rises 62.1295 -> 63.5973 under projection-v3 while the arm does not move at all, because the
arm is already normalised. Section 2 says the same thing from the other side: against a lock
comparator that HAS the node, the arm's SLU delta is -0.1453.

**Reading.** The plan's headline SLU advantage over the tool-free base is, in the main, delivery
post-processing that the v3 node supplies -- not additional slot-filling capability. The advantage
that survives a like-for-like normalised comparison is **intent** (+2.2222 pp against the base,
CI95-disjoint from zero). Any claim that the default plan "adds +1.5 SLU" without naming the
normalisation asymmetry would be wrong.

Source: `score-contrasts.json`, `projection_v3`, `projection_v3_contrasts`, `train_symmetric`,
`train_symmetric_contrasts`.

## 4. Frontier row (owner decision 75)

| cell | official SLU | official intent | GPU-h / 1,080 | contacts / row | prefilled tok / row | basis |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| **PLAN** | **63.6304** | **82.2222** | **1.7579** | **4.0963** | **8,353.2** | ESTIMATE |
| B8a (B5e base) | 63.78 | 81.85 | 3.8709 | 5.014 | 46,796.0 | PROXY |
| B8a (B1 base) | 62.67 | 81.76 | 3.6819 | 5.023 | 45,730.5 | PROXY |
| B5e | 62.34 | 80.09 | 3.8709 | 5.014 | 46,796.0 | PROXY |
| B1r | 62.23 | 80.09 | 3.8507 | 5.040 | 26,071.9 | measured |
| B1-notool | 62.13 | 80.00 | 1.6108 | 4.104 | 8,019.8 | measured |
| B1 | 61.14 | 80.19 | 3.6819 | 5.023 | 25,933.0 | measured |
| IDX | 54.76 | 77.59 | 1.3340 | 4.181 | 3,379.1 | measured |
| B4b | 51.09 | 78.52 | 3.4651 | 5.006 | 26,197.0 | measured |
| B0 | 48.67 | 77.59 | 1.0540 | 2.000 | 12,328.7 | PROXY |

**PLAN is on both Pareto planes** (`plan_is_on_the_gpu_hour_frontier: true`,
`plan_is_on_the_prefilled_token_frontier: true`):

- GPU-hour plane: B0 48.67 @ 1.054 -> IDX 54.76 @ 1.334 -> B1-notool 62.13 @ 1.611 -> **PLAN 63.63 @
  1.758** -> B8a 63.78 @ 3.871.
- Prefilled-token plane: IDX 54.76 @ 3,379.1 -> B1-notool 62.13 @ 8,019.8 -> **PLAN 63.63 @ 8,353.2**
  -> B8a 63.78 @ 46,796.0.

PLAN reaches within **0.15 SLU** of the provisional lock at **45.4 %** of its GPU hours and **17.8 %**
of its prefilled tokens per row. Decision-75 triples: PLAN vs B1-notool +0.8538 SLU pp per GPU-hour
and +0.1797 pp per 1,000 prefilled tokens; PLAN vs B5e node-applied -0.0826 and -0.0174.

`scripts/analysis/slurp_module_frontier.py` cannot accept a new cell -- its collect stage iterates
hard-coded module-level `ARMS` and `CELLS` tables -- so this row is computed by this read. Adding it
to that script is a separate source edit and is NOT done here.

Source: `frontier.json` (`66efa4ec7de7004cc2a5d0d6d487483ac0ace32e2ea3efb9d03097b0d69418c7`).

## 5. E20 compaction diagnostic (mandatory)

| | arm | base |
| --- | ---: | ---: |
| declared policy | compact-or-abstain (item E20) | compact-or-abstain (item E20) |
| rows compacted | **0** | 0 |
| contacts compacted | **0** | 0 |
| rows with a context-fit receipt | 1,080 | 0 |
| contacts seen in the receipts | 4,424 | 0 |
| one receipt per row | yes | no |
| agrees with the flight receipt | yes | yes |

Zero rows compacted, so compaction contributes nothing to the arm's cost and there is no compacted /
uncompacted outcome split to measure (`comparable: false`). The base carries no context-fit receipts
at all -- it predates the E20 receipt -- which is an instrumentation asymmetry, not a behavioural one.

Fit evidence from the paired fit run: 4,424 request-fit receipts over 17,696 endpoints,
`every_request_fits: true`, maximum required 14,413 tokens against a 24,576-token slot, minimum margin
10,163 tokens at the Planner.

Source: `compaction.json` (`e2b161e88be6f47e478e3533eef62aef849d54cb2c569b6a7ef3eb35d9cf0e81`),
`structural.json` (`210076e95a2cc64c45fcccdd1550b53b81e8cc6035ce62c2d1e81cc318c9ece0`),
`efficiency.json` (`19524fa9c4174925b1af903f3a358a6e72662c8222008d3551833dd9f3ad58ba`) `costs.arm.fit`.

## 6. Per-scenario tables

Intent (left = base, right = arm) and pooled SLU-F1 micro, 60 rows per scenario:

| scenario | n | base intent | arm intent | d intent | saves | harms | base SLU | arm SLU | d SLU |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 60 | 86.67 | 88.33 | +1.67 | 1 | 0 | 72.90 | 76.75 | +3.85 |
| audio | 60 | 78.33 | 76.67 | -1.67 | 0 | 1 | 61.94 | 48.17 | **-13.76** |
| calendar | 60 | 80.00 | 80.00 | 0.00 | 1 | 1 | 63.96 | 65.64 | +1.68 |
| cooking | 60 | 85.00 | 85.00 | 0.00 | 1 | 1 | 64.49 | 63.21 | -1.27 |
| datetime | 60 | 88.33 | 90.00 | +1.67 | 2 | 1 | 70.77 | 73.37 | +2.61 |
| email | 60 | 86.67 | 88.33 | +1.67 | 1 | 0 | 54.41 | 61.78 | +7.37 |
| general | 60 | 41.67 | 43.33 | +1.67 | 2 | 1 | 17.78 | 30.23 | **+12.45** |
| iot | 60 | 88.33 | 88.33 | 0.00 | 0 | 0 | 68.18 | 66.37 | -1.82 |
| lists | 60 | 81.67 | 83.33 | +1.67 | 1 | 0 | 50.55 | 57.45 | +6.90 |
| music | 60 | 70.00 | 80.00 | **+10.00** | 6 | 0 | 47.10 | 48.75 | +1.65 |
| news | 60 | 81.67 | 83.33 | +1.67 | 2 | 1 | 64.86 | 68.77 | +3.90 |
| play | 60 | 63.33 | 88.33 | **+25.00** | 17 | 2 | 52.33 | 55.39 | +3.06 |
| qa | 60 | 78.33 | 75.00 | -3.33 | 0 | 2 | 57.77 | 62.65 | +4.88 |
| recommendation | 60 | 90.00 | 90.00 | 0.00 | 1 | 1 | 67.48 | 66.49 | -1.00 |
| social | 60 | 75.00 | 73.33 | -1.67 | 0 | 1 | 56.79 | 58.32 | +1.53 |
| takeaway | 60 | 85.00 | 85.00 | 0.00 | 1 | 1 | 60.66 | 61.79 | +1.13 |
| transport | 60 | 86.67 | 88.33 | +1.67 | 3 | 2 | 66.77 | 66.68 | -0.09 |
| weather | 60 | 93.33 | 93.33 | 0.00 | 1 | 1 | 75.85 | 70.84 | -5.01 |

**Band (diagnostic, never a gate).** Zero scenarios breach the intent band: no scenario has a CI95
upper bound below zero, and `decision_17_flagged_scenarios` is empty. The three scenarios with a
negative intent delta are `qa` (-3.33, 0 saves / 2 harms), `audio` (-1.67, 0/1) and `social`
(-1.67, 0/1) -- one or two rows each. The intent gain is concentrated, not diffuse: `play` (+25.00,
17 saves) and `music` (+10.00, 6 saves) supply 23 of the 40 saves.

The largest scenario-level SLU movements are `general` +12.45 and `audio` -13.76. Both are single
scenarios of 60 rows and neither is separately powered; they are listed as diagnostics.

Source: `per-scenario-tables.json`
(`19ad6034802c366df6fcfc39116493302904036c529c59cf626a38da9529330c`).

## 7. Structural counts

| | arm | base |
| --- | ---: | ---: |
| contacts | 4,424 | 4,432 |
| contacts per row | 4.0963 | 4.1037 |
| requests carrying a `tools` array | **0** | **0** |
| every `tool_choice` is none | yes | yes |
| tool calls (trace) | 0 | 0 |
| tool calls (manifest) | 0 | 0 |
| distinct tool-schema sha256 | 1 | 1 |
| ReAct-exhaustion rows | 0 | 0 |
| role contacts: perception / solver / reviewer / planner | 1,080 / 1,118 / 1,118 / 1,108 | 1,080 / 1,120 / 1,120 / 1,112 |

**Delivery normaliser receipts (arm).** 1,080 rows carry a receipt, one per row; 1,079 applied and 1
not applied (the single malformed row); 102 rows changed, of which 71 filler-only and 34 label
(76 fillers and 34 labels changed in total); 978 rows whose delivered text is byte-identical to the
Solver draft; 977 rows with rendering suppressed. The base carries no normaliser receipts at all
(0 of 1,080) -- the asymmetry section 3 quantifies.

**Perception request delta.** 1,080 rows compared, 0 offenders, `claim_holds: true`: every row's
Perception request differs from the base's only inside the armed key set.

**Pins.** Arm baseline fragment `slurp-native-default-plan-lock-baseline-v1`
(`2cd5060579bcf341a4533c077c4ebddce9bbeb635e70d2c63fbe0e6bb66b9ae1`), knowledge snapshot
`ee4bc99e4935015ce27a510bee4963c4ddb8939bd2f4ae847e8d4c9e97e381c8`, protocol hash
`5a1868d329cb8881fe7697c88ac94632f3f05c1ca6279a2af70cec685b15d4c4`. Base fragment
`slurp-native-anchor-exemplars-k20-notool-v1`
(`50d210c0ee559778c4031152fd57de227aea5ffa6b9a3ed0f62c3f51286d8440`), knowledge snapshot
`a43d8b93f93c4c6d294c8f23b7aa0dd5cc340d00d566bff88880d931ddf3ef80`, protocol hash
`743313686772b96d0e07603188b3437990660538706a3c4cd7a1e8c66029e8b8`. Both arms ran the same controller
policy `phase-native-candidates-review-revise-v1` through the same executor
`openjiuwen-workflow-v1`.

Source: `structural.json` (`210076e95a2cc64c45fcccdd1550b53b81e8cc6035ce62c2d1e81cc318c9ece0`).

## 8. Efficiency and cost

| number | arm | base |
| --- | ---: | ---: |
| prefilled tokens per row | 8,353.2 | 8,019.8 |
| client prompt tokens per row | 34,020.6 | 33,082.0 |
| generated tokens per row | 244.15 | 246.42 |
| GPU hours per 1,080 rows | **1.7579** | **1.6108** |
| generation wall seconds | 6,946.03 | 6,400.41 |
| contacts per minute (RELEASE records) | 39.92 | 42.91 |
| contacts per row | 4.0963 | 4.1037 |
| cache hit share | 0.7545 | 0.7576 |
| truncations | 0 | 0 |
| projected 13,078-row read hours | 21.287 | 19.506 |

**Cost delta: +0.1471 GPU-h per 1,080 rows, +9.13 %.** `cost_is_lower_than_the_base: false`.

**Where the cost went.** The per-position prefill decomposition localises it: of the +333.4 prefilled
tokens per row, **+338.7 lands at position 1, the Solver**, while Perception (-7.1), Reviewer (-0.2),
Planner (+3.9) and the three revisit positions (-0.6, -0.5, -0.7) are flat. That is where the v2
slot-contract cards enter. The stage lists four candidate causes and the measurements rule three out:
compaction moved 0 rows (section 5), the delivery normaliser is model-free and makes no contact, and
the review-loop marker changes no contact count by itself (contacts per row 4.0963 against 4.1037 --
the arm makes marginally FEWER contacts per row than the base). Attribution is descriptive, never
causal.

**Join quality and the ESTIMATE basis.** The base's server-log join is exact: 4,432 / 4,432 contacts,
`is_a_measurement: true`. The arm's is 4,401 / 4,424, **99.4801 %**, so the arm's per-role and
per-position figures are ESTIMATES -- which is why the frontier row in section 4 carries
`token_basis: ESTIMATE`. The mismatch profile bounds the estimate:

- 23 mismatched contacts, 0.5199 % of the flight's contacts, across 18 distinct sample ids.
- The signed discrepancy `server_minus_client_tokens` **sums to exactly 0** (mean 0.0, min -9,679,
  max +9,679): the join is a permutation within the flight, not a loss. Flight TOTALS -- 9,021,502
  prefilled tokens, 36,742,293 prompt tokens, the GPU hours and the sealed wall -- are sums over the
  complete set of server tasks in the sealed window and are unaffected.
- The mismatched contacts carry 13,055 prefilled tokens, **0.1447 %** of the flight's prefill. Worst
  case, with every one of those tokens attributed to the wrong position, the per-position figures move
  by at most **12.1 tokens per row** -- 3.6 % of the +338.7 Solver delta.
- They sit at positions 0_perception (7), 2_reviewer (5) and 3_planner (11), in slots 1/2/3. **None
  sits at 1_solver**, so the Solver attribution is drawn entirely from exactly-matched contacts.

Per-slot client contacts equal per-slot server tasks exactly on both arms (arm 1,063 / 1,172 / 1,154 /
1,035; base 1,093 / 1,146 / 1,129 / 1,064).

**Budget.** Run-cumulative across every attempt of this run id: 4,424 model calls against 11,880
planned, 12,589.60 s audio; `within_ceiling: true`, `audio_within_ceiling: true`.

Both arms flew on the same resident serving session
`serving-slurp-native-candidate-five-train-a-np4-v1` at the same np4 geometry, 4 serving slots, slot
occupancy 0.7876 (arm) and 0.7873 (base). `server.log` is deliberately NOT pinned by whole-file digest
-- it is still being appended by later flights on the same session -- so the join is scoped to each
flight's own sealed contact window instead.

Source: `efficiency.json` / `throughput-tables.json`
(`19524fa9c4174925b1af903f3a358a6e72662c8222008d3551833dd9f3ad58ba`).

## 9. Process incident during this read, and one defect found

**Incident.** Four `plan_cell_read.py` processes were found alive simultaneously: killed harness
wrappers had left their WSL Python children running. Two were `contrast` processes racing each other
over the same official-scoring output paths, and a stray `lock` process wrote the v3 cross-check score
file between this read's `exists()` check and its `open("x")`, raising `FileExistsError`. That crash
was the score-once guard working as designed, not a scoring fault. The younger duplicate `contrast`
was stopped; the further-along processes were allowed to finish; the concurrently running replicate
campaign was not touched.

**Audit.** Because a race could in principle have scored a half-copied input, every derived copy was
verified by sha256 against its canonical copy. All matched, 1,080 rows each: arm
`2dcaa925ab7dad77...`, base `81b370bfceb49ff9...`, lock `3d861012bfbbf267...`, consistent across the
`v3/`, `symmetric/` and `lock-node/v3-cross-check/` scoring roots. **No number in this document was
produced from a torn input.**

**Defect (open).** `_score_copies` in `plan_cell_read.py` copies an arm's `outputs.jsonl` into its
scoring directory with a bare `shutil.copyfile` and **no digest check**, unlike `outputs_copy`, which
verifies the copy against the sealed source and exits on mismatch. Under concurrency a partially
written copy can therefore be scored silently into an official number. The audit above shows it did
not happen here, but the guard is missing and should be added: re-verify the target copy against the
source digest after the copy, exactly as `outputs_copy` does. Not fixed by this read.

**Consequence for practice.** Killed background wrappers do not kill their WSL children. Before
launching an analysis stage, probe for an already-running instance; two concurrent stages writing the
same official-scoring root is a correctness hazard, not merely a wasted CPU.

## 10. Harness-admission consequence

**No module is decided by this read.** Cell PLAN flies the whole default plan as one arm; it is not a
one-factor cell and it isolates nothing. NEUTRAL here is a statement about the assembled plan, not
about M1, M3, M4b or any other constituent, and no harness-admission entry, switch, falsifier or
status is created, changed or retired by this document.

What this read does establish, and what follows:

1. **The default plan is retained.** NEUTRAL admits it to continued use under the section-8 gate: it
   is non-inferior to the tool-free base on both guards and at parity with the provisional lock.
2. **The candidate v2.0 lock numbers are 63.6304 / 82.2222**, recorded in section 0. **The lock record
   supersedes the provisional one only once PLANr reads** and the pair replicates. Until that read
   lands, `docs/results/2026-09-20-slurp-v2-provisional-lock-v1.md` remains the standing provisional
   lock, and no downstream cell should cite 63.6304 / 82.2222 as a locked base.
3. **Cost is registered against the plan**: +9.13 % GPU-h over the tool-free base, localised at the
   Solver position, with PLAN nonetheless on both Pareto planes. A future efficiency cell targeting
   the v2 slot-contract cards has its measured target here: 8,353.2 prefilled tokens per row, of which
   6,458.8 are the Solver's.
4. **The normalisation asymmetry of section 3 must travel with any quoted SLU delta.** A like-for-like
   normalised comparison puts the plan +0.03 against the tool-free base and -0.15 against the
   provisional lock.

Nothing in this document registers an arm, opens an attempt, edits the results ledger or writes an
exposure-ledger row.

## Artefacts

Every number above comes from one of these, under
`SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-DEFAULT-PLAN-LOCK-PAIRED-ANALYSIS-V1/`:

| file | sha256 |
| --- | --- |
| `compaction.json` | `e2b161e88be6f47e478e3533eef62aef849d54cb2c569b6a7ef3eb35d9cf0e81` |
| `efficiency.json` | `19524fa9c4174925b1af903f3a358a6e72662c8222008d3551833dd9f3ad58ba` |
| `frontier.json` | `66efa4ec7de7004cc2a5d0d6d487483ac0ace32e2ea3efb9d03097b0d69418c7` |
| `lock-comparison.json` | `fa54e32deebcfc8df1470346ccd1fc52826b98fafbe740d1a628f1608e1a430c` |
| `per-scenario-tables.json` | `19ad6034802c366df6fcfc39116493302904036c529c59cf626a38da9529330c` |
| `plan_cell_read.py` | `72952d20a22dbeea5e0f67e4343c25a3f74fbea28451fd39b938b36877443af3` |
| `score-contrasts.json` | `3e09c7aff96359f8a16c7e4f271443f103b39635459c4b4514b21d6a4c3397b7` |
| `structural.json` | `210076e95a2cc64c45fcccdd1550b53b81e8cc6035ce62c2d1e81cc318c9ece0` |
| `throughput-tables.json` | `19524fa9c4174925b1af903f3a358a6e72662c8222008d3551833dd9f3ad58ba` |

The read's own `README.md` beside them carries the full sealed-input table (every sealed
`scores.json`, `run-manifest.json`, `outputs.jsonl`, `phases.json`, `trace.jsonl` and
`flight-receipts.json` with its sha256) and the exact seven-stage command that regenerates every
artefact in order: `stop`, `structural`, `contrast`, `lock`, `efficiency`, `frontier`, `verdict`.
