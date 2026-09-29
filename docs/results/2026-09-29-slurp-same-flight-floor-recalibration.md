# Same-flight measurement floor re-calibration: impact of flooring on the W-SV-1 contrast half-width (MODEL-FREE)

Written 2026-09-29 by Claude Opus 5.5 in the worktree `fable/floorcal`, forked from master `3adf05958`. The analysis
is model-free: 0 model, tokenizer, encoder, server or GPU contacts, and no `core.flight.cli` invocation. Nothing is
applied here. The `FLOOR_TABLE` diff in section 6 is text for the coordinator.

**Sources.** The gate is `scripts/checks/stage3_effect_floor_check.py` at master `3adf05958`. The W-SV-1 read
artefacts are under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1/`:

- `twin-null/score-contrasts.json`, sha256 `f4d6930c…94fd`
- `knob/score-contrasts.json`, sha256 `757f3cab…0b41`

Both hashes match `docs/results/2026-09-29-slurp-wsv1-fold-a-column-read.md:15-20`. The inner-loop outputs are under
`$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SEALED-CREDIT-INNER-LOOP-RUN-1-V1/`:

- `candidates.json`, sha256 `812cbb196598f06ae350e23c4d5ed0e7d15a66574ec1d417681ced1d614acc2a`
- `nomination.json`, sha256 `cafaa76412a65b02097a01f737a8f9d9e11d3ef1ea9c9c475faa48a14de9fda9`

The acceptance code is `src/speech_aware_evidence_acquisition/analysis/sealed_credit/accept.py` on branch
`fable/innerloop`. This note contains no utterance text, gold labels or model output, only counts, rates, ids and
hashes.

## 1. What the gate holds and how it compares

**The table.** `FLOOR_TABLE` spans `scripts/checks/stage3_effect_floor_check.py:247-351`. The three same-flight rows
that bear on this question are quoted verbatim, with their source strings abridged:

```python
# :262-275
    "same-flight-supply-variant": Floor(
        source=( ... "until an instrument cell has flown and measured that null, the provisional floor "
            f"anchor is {INSTRUMENT_NOTE} section 2a/2d row 2 (cell ROLL-AA, h_within "
            "0.735 SLU / 0.000 intent at n = 200) -- same number as same-flight-paired, ..." ),
        sampling=((200, 0.735),),
    ),
# :285-301
    "same-flight-perception-variant": Floor(
        source=( ... "provisional floor anchor is ... (cell ROLL-AA, h_within 0.735 SLU / 0.000 intent at n = 200)" ... ),
        sampling=((200, 0.735),),
    ),
# :319-328
    "same-flight-shadow-relisten": Floor(
        source=( f"{INSTRUMENT_NOTE} section 2a/2d row 2 (cell ROLL-AA, h_within 0.735 SLU / 0.000 intent at n = 200); ..." ),
        sampling=((200, 0.735),),
    ),
```

The other rows are:

- `same-flight-paired` (`:255-261`): `sampling=((200, 0.735),)`, which is ROLL-AA as measured.
- `offline-sealed-pool`: 0.67 at n = 625.
- `cross-flight-with-in-chain-replicate`: sampling 1.474 at 625, 1.2525 at 1,000 and 1.2485 at 1,080, with a bar of
  3.0 at 625 and 2.5 at 1,080.
- `cross-flight-no-replicate`: refused.
- `form-proof`: no numeric floor.

**How the comparison works.**

| aspect | behaviour | where |
| --- | --- | --- |
| field compared | `stage3_measurement.expected_effect_pp`, a single float | `_parse_declaration` `:661-667` |
| comparison | `effect-below-floor` iff `claims_benefit` and `effect_pp < floor` | `:901-918` (test at `:905`) |
| floor | `floor_for(design, rows)`, purpose `benefit`: the max of the sampling anchor and the bar anchor, each scaled | `:385-427`, called at `:853` |
| n scaling | `anchor_h * sqrt(anchor_n / rows)` from the anchor nearest in log n; same-flight: `0.735 * sqrt(200 / 1080) = 0.3163` | `:365-383` (`:377`) |
| metric | **not modelled**: `primary_metric` is free text, "reported, never enforced" (`:43`); one floor per design | `:43`, `:716-719` |
| intent vs SLU | **not separate**. The 0.735 anchor is the ROLL-AA **SLU** half-width. The ROLL-AA intent half-width (0.000) is cited in the source text only, and the gate applies 0.3163 to whatever metric the cell names | `:269`, `:274` |
| no-harm margin | `floor_for(..., purpose="harm")`: the sampling part alone. For same-flight this is the same 0.3163 | `:409-413`, `:861-896` |
| rows | `stage3_measurement.rows`, else the fragment's `population.count` | `:669-682` |

## 2. W-SV-1 half-widths, exact

All figures come from the paired whole-cluster bootstrap: cluster key `sample_id`, 10,000 replicates, seed
20260928, n = 1,080, TRAIN gold through `slurp-slu-official-train`. `ci95_half_width_pp` is (hi - lo) / 2.

| contrast | metric (artefact key) | delta pp | CI95 pp | **half-width pp** | sigma_hat pp | saves / harms |
| --- | --- | ---: | --- | ---: | ---: | --- |
| twin T-A | intent `per_row.scenario_action_exact` | 0.0 | [0.0, 0.0] | **0.0** | 0.0 | 0 / 0 |
| twin T-A | SLU `pooled_micro.slu_f1_micro` | +0.37320 | [-0.14324, +0.92159] | **0.53242** | 0.27089 | -- |
| twin T-A | span `pooled_micro.span_f1_micro` | +0.37787 | [-0.26863, +1.07229] | 0.67046 | 0.34175 | -- |
| contrast B-A | intent `per_row.scenario_action_exact` | +0.37037 | [-0.09259, +0.92593] | **0.50926** | 0.26078 | 6 / 2 |
| contrast B-A | SLU `pooled_micro.slu_f1_micro` | -0.45820 | [-1.85220, +1.12093] | **1.48656** | 0.75994 | -- |
| contrast B-A | span `pooled_micro.span_f1_micro` | -0.75092 | [-2.47841, +1.09077] | 1.78459 | 0.91221 | -- |
| contrast B-A | per-row SLU `per_row.slu_f1_f1` | -0.12849 | [-1.05078, +0.78325] | 0.91702 | 0.47081 | 45 / 54 |

The twin rows are from `twin-null/score-contrasts.json` and the contrast rows from `knob/score-contrasts.json`.

**Scaling to other n.** The table scales each half-width by `h * sqrt(1080 / n)`. These are **extrapolations**:
they assume the same per-row variance and, for intent, the same discordance rate.

| half-width | n = 200 (extrap.) | n = 625 (extrap.) | n = 1,080 (measured) | n = 2,000 (extrap.) |
| --- | ---: | ---: | ---: | ---: |
| twin intent | 0 | 0 | 0 | 0 |
| twin SLU | 1.2372 | 0.6999 | 0.5324 | 0.3912 |
| contrast intent | 1.1834 | 0.6694 | 0.5093 | 0.3742 |
| contrast SLU | 3.4545 | 1.9541 | 1.4866 | 1.0924 |
| current floor (for reference) | 0.735 | 0.4158 | 0.3163 | 0.2324 |

**Ratios to the current floor at n = 1,080:**

- contrast intent: 0.5093 / 0.3163 = 1.61
- contrast SLU: 1.4866 / 0.3163 = 4.70
- twin SLU: 0.5324 / 0.3163 = 1.68

**The intent half-width is set by discordance, not by the design.** Intent is a paired binary, so its half-width is
about 1.96 * sqrt(d) / n * 100, where d = saves + harms. For W-SV-1, d = 8, and the normal approximation gives
0.5133 against the bootstrap's 0.5093. A knob that moves more rows gets a wider interval, and a knob that only saves
gets a narrower one. With 0 harms, e net saves give a CI95 lower bound above zero once P(no save row resampled)
≈ exp(-e) < 0.025, which is e ≥ 4 rows = **0.37 pp** at n = 1,080. So 0.51 is the half-width for one knob with
d = 8. It is not a constant of the design.

## 3. Registered same-flight cells

`configs/experiment` and `configs/baseline` contain **no** `same-flight-` string. Every same-flight declaration sits
in a readiness package: `registered-facts-v1.json` is precedence 1, and the preregistration fence mirrors it. The
same five packages are the only ones on any local branch, based on `git grep` of `docs/readiness` and `configs`
across all refs.

**Proposed floors at n = 1,080:** intent 0.5093 and SLU 1.4866. P-SV-2's primary metric (presence) has no anchor
under either the current or the proposed table.

| cell (run id) | state | design | declared `expected_effect_pp` / claims_benefit | primary metric | (a) clears 0.3163? | (b) clears proposed floor? |
| --- | --- | --- | --- | --- | --- | --- |
| `SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1` | flying (driver) | supply-variant | **0.79 / true** (`w4-sv-fold-a-v1/registered-facts-v1.json:649`) | SLU-F1 of b-w4 - a-agree, intent guard (`:652`) | **yes** (0.79 > 0.3163) | **no** (0.79 < 1.4866, SLU): would draw `effect-below-floor`, **blocking** |
| `SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1` | flown, read | supply-variant | 0.09 / false (`wsv1-fold-a-v1/registered-facts-v1.json:579`) | SLU-F1, intent guard (`:582`) | no (no finding: claims false) | no (no finding) |
| `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1` (E4-1) | flipped, queued `SAEA-Queue-E4` | shadow-relisten | 0.0 / false, per column 0.0 (`e4-relisten-fold-a-v1/registered-facts-v1.json:532`, `:535-538`) | SLU-F1 per shadow column; intent identical by construction (`:539`) | no (no finding) | no (no finding) |
| `SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1` | countersigned, not flipped | perception-variant | 0.0 / false (`psv1-fold-b-v1/registered-facts-v1.json:493`) | **intent** of the level-2 branch Solver column, SLU guard (`:497`) | no (no finding) | no (no finding) |
| `SAEA-SLURP-STAGE3-PSV2-FOLD-B-V1` | countersigned, not flipped | perception-variant | 0.0 / false (`psv2-fold-b-v1/registered-facts-v1.json:471`) | **gold-on-list presence** (`:475`), with intent beside and never gating | no (no finding) | no (no finding; presence has no anchor) |
| the four `-SMOKE-4-V1` cells (W4SV, WSV1, RELISTEN, PSV1, PSV2) | -- | `form-proof`, 0.0 / false | e.g. `w4-sv-fold-a-v1/registered-facts-v1.json:630-633` | none | n/a | n/a (unaffected) |

**Source sentences.**

- **W4-SV.** `:651`: "Expected 0.79 pp from the cross-flight W4 read; provisional floor 0.3163 pp at n = 1,080; bar
  = the twin null. ESTIMAND CAVEAT…" The 0.79 is a **cross-flight full-system** SLU effect, CI95 [-0.56, +2.12],
  transferred to a Solver-local first-visit estimand.
- **W-SV-1.** `:581`: "…expected_effect_pp is 0.09. That is BELOW this design's provisional floor 0.3163 pp … and
  the cell declares claims_benefit false".
- **E4-1.** `:534`: "Ruling 7: both columns declare expected_effect_pp 0.0 with claim ceiling 'nominated', since no
  measured analogue exists…". The ceilings it states are 0.71-3.0 pp SLU and 0 pp intent.
- **P-SV-1.** `:496`: "…row 139: no prior, so the declaration is 0.0 nominated with the ceiling beside". The ceiling
  is 3.89 pp intent. The note gives a rank-2 conversion of 26.98 %, but the design's own promotion rate is
  UNMEASURED.
- **P-SV-2.** `:474`: "…no prior, so the declaration is 0.0 nominated…". The presence ceiling is 4.54 pp, and the
  delivered-intent ceiling is "about 0.5 pp".

**Simulated gate.** The `evaluate()` of the check was run in the worktree three ways: with the current table, with
the three same-flight rows re-anchored to `((1080, 0.5093),)`, and with them re-anchored to `((1080, 1.4866),)`.

- Current and 0.5093: 17 findings, identical.
- 1.4866: 18 findings. The single new finding is `effect-below-floor` **blocking** on
  `SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1`.

The gate already exits 1 on master `3adf05958`, for an unrelated pre-existing reason: an `unparsable-declaration`
(blocking) on `SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-V1`. The gate also treats `SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1` as
in scope, with the ledger `consumed` column reading `no`, even though that cell has flown and been read.

**Would the reads be underpowered? (No retroactive refusal is implied: W4-SV is flying and E4-1 is queued.)**

- **W4-SV.** The gating read is SLU-F1. If B-A has W-SV-1's contrast half-width of 1.4866, an effect of 0.79 would
  have a CI95 that covers zero. It needs about n = 1,080 * (1.4866 / 0.79)^2 ≈ **3,824** rows at CI-excludes-zero
  (extrapolation). The read's own rule is NOMINATED iff the SLU lower bound > 0 AND the point > twin bar, so this is
  underpowered for 0.79. The twin bar (W-SV-1: 0.9056) alone would need n ≈ 1,419. The intent guard's twin null is
  plausibly 0, as in W-SV-1, so any net intent harm row fails the guard.
- **E4-1.** It declares 0.0 and stated ceilings of 0.71-3.0 pp SLU. Only the top of that range clears a 1.49 pp
  contrast half-width, so a "NOT NOMINATED" is the likely outcome unless the effect is at least about 1.5 pp.
  Intent is identical by construction, so intent power does not apply.
- **P-SV-1.** Intent is primary. A 0.51 pp intent floor is about 5.5 net rows at d ≈ 8. Resolving the declared
  ceiling (3.89 pp = 42 rows) would take a conversion rate of at least about 13 %. This is adequately powered for
  anything at the ledger's rank-2 conversion scale. That scale is not a declaration.
- **P-SV-2.** Presence is primary and has no anchor. The intent effect it reports beside is about 0.5 pp at the
  ledger's 12 % rank-3 conversion, which sits right at the 0.51 floor: **borderline**.

## 4. Sealed-credit inner loop run 1 under the proposed floors

**Where the floor comes from.** `accept.py` imports the floor **from the gate** and does not hard-code it
(`fable/innerloop` `accept.py:46-72`). `design_guard_and_floor` loads `scripts/checks/stage3_effect_floor_check.py`
and calls `gate.floor_for(design, rows, purpose="harm")` for the SLU **guard** and `purpose="benefit"` for the
**floor** (`:65-66`). A change to a table value therefore flows through automatically.

**The metric caveat.** `accept.py` compares `predicted_intent_pp > floor_pp` (`:84-88`) and
`predicted_slu_pp < -guard_pp` (`:82`), and both numbers come from the same metric-blind `floor_for`. Today they are
the same 0.3163, a number anchored on SLU. A single-number table can carry only one of 0.5093 or 1.4866. A split by
metric needs `floor_for` to take a metric argument and `accept.py` to pass `"intent"` for the floor and `"slu_f1"`
for the guard (section 6).

**Other facts about run 1.**

- All 16 candidates were scored against `read_design` `same-flight-supply-variant`, n = 1,080 (`candidates.json`
  keys `read_design`, `rows`). This includes the Perception-side knobs `presentation_id` and `min_candidates`, which
  P-SV-1 and P-SV-2 would read under `same-flight-perception-variant`.
- The run nominated `phase_supply.k` = 10 (`nomination.json` `/nominated` true). Its evidence
  (`/candidate/evidence/intent_delta_pp`) is a cross-pool read, VAR-1 PLANR vs VAR-1 ex-k10: +0.48 pp intent,
  CI95 [-1.12, +2.24], n = 625.

**Re-applying the rule with the proposed floors.** The floor applies to predicted intent and is 0.5093. The SLU
guard is shown as the contrast half-width 1.4866 (the proposal applied mechanically) and as the W-SV-1 twin bar
0.9056 (the Q2 ruling's literal "twin null").

| rank | knob = value | pred. intent pp | pred. SLU pp | unobserved | as run (0.3163 / 0.3163) | proposed floor 0.5093 | guard 1.4866 | guard 0.9056 | clears under proposal |
| ---: | --- | ---: | ---: | --- | --- | --- | --- | --- | --- |
| 1 | `phase_supply.k` = 10 | 0.48 | -0.2827 | no | clears, **NOMINATED** | **no** (0.48 < 0.5093) | kept | kept | **no** |
| 2 | `presentation_id` = rank-visible-v1 | 0.287 | n/m | no | no | no | kept | kept | no |
| 3 | `min_candidates` = 3 | 0.0536 | n/m | no | no | no | kept | kept | no |
| 4-12 | nine "+1 step" / untried knobs | 0.0 | 0.0 | **yes** | no | no | kept | kept | no |
| 13 | `release_swap` = slot-contracts-w4-v1 | -0.0926 | +0.4269 | no | no | no | kept | kept | no |
| 14 | `deliver_normaliser` = off | -1.9444 | n/m | no | no | no | kept | kept | no |
| 15 | `phase_supply.k` = 30 | 0.3704 | -0.4582 | no | clears the floor, **guard-discarded** | no | **kept** (-0.458 > -1.487) | **kept** | no |
| 16 | `reviewer_planner` = off | -1.8519 | -3.3909 | no | discarded | no | discarded | discarded | no |

"n/m" means not modelled (`predicted_slu_pp` null).

**Result: confirmed. No candidate clears under the proposed floors.** The run-1 nomination (k = 10, 0.48 pp) falls
0.029 pp short of 0.5093.

A side effect goes the other way: k = 30 is guard-discarded today only because the SLU guard is 0.3163. Under either
wider guard it is kept. It still fails the intent floor (0.3704 < 0.5093), and its measured same-flight read (the
W-SV-1 knob) is already NOT NOMINATED.

The k = 10 case is sensitive to discordance, as section 2 shows. At n = 1,080, +0.48 pp ≈ 5.2 net rows. CI95
excludes zero if harms are about 0 (5 saves / 0 harms: exp(-5) = 0.0067 < 0.025). It covers zero if harms are 2 or
more (d ≥ 9, so 1.96 * sqrt(d) ≈ 5.9 > 5.2). At W-SV-1's k = 30 ratio of 6 saves to 2 harms, it would not resolve.

## 5. Power framing

At n = 1,080, with contrast half-width h, the smallest effect that can read CI-excludes-zero is about h. Under the
proposal, the smallest declared effect a claims-benefit cell should carry at n = 1,080 is:

| design | intent | SLU-F1 | basis |
| --- | ---: | ---: | --- |
| `same-flight-supply-variant` | **0.51** | **1.49** | W-SV-1 knob contrast (measured) |
| `same-flight-perception-variant` | 0.51 (provisional) | 1.49 (provisional) | borrowed from W-SV-1. A Perception fork re-draws the candidate list, so its twin intent null need not be 0, and d may be larger |
| `same-flight-shadow-relisten` | n/a (intent identical by construction) | 1.49 (provisional) | borrowed from W-SV-1. A shadow column changes only accepted replacements, so d may be smaller |
| `same-flight-paired` (unchanged) | -- | 0.735 at 200 → 0.3163 at 1,080 | ROLL-AA (measured) |

**What n is needed.** Using h(n) = h_1080 * sqrt(1080 / n) (extrapolation):

| effect to read | metric | h at 1,080 | n needed (h ≤ effect) | DEV-2000-ADDED (n = 2,000) h | sufficient at 2,000? |
| --- | --- | ---: | ---: | ---: | --- |
| +0.48 (inner-loop k = 10) | intent | 0.5093 | **≈ 1,216** | 0.3742 | **yes** (0.374 < 0.48), with discordance like W-SV-1's |
| +0.79 (W4-SV declaration) | SLU-F1 | 1.4866 | ≈ 3,824 | 1.0924 | **no** |
| +0.79 against the twin bar only | SLU-F1 | 0.9056 | ≈ 1,419 | 0.6655 | yes, for the bar clause only; the CI clause still fails |
| 1.0 pp | SLU-F1 | 1.4866 | ≈ 2,387 | 1.0924 | no (marginal) |

**DEV-2000-ADDED.** At n = 2,000 the roster suffices for a +0.48 pp intent effect only in this sqrt(n) sense, and
only if the knob's discordance rate is about W-SV-1's (8 / 1,080). It does not suffice for sub-1 pp SLU-F1 effects.
The roster is also a DEVEL roster: decision 28 applies, so a read there is a development number, not a test claim.

## 6. Recommendation to the coordinator

1. **Split the floor by metric. Do not collapse it to one number.**
   - A single 1.4866 would refuse every intent-primary cell that the same-flight design can in fact resolve, down to
     4 clean net rows = 0.37 pp.
   - A single 0.5093 would keep admitting SLU declarations (W4-SV's 0.79) that the design cannot see.
   - The current 0.3163 is below **both** measured contrast half-widths, by 1.61x and 4.70x.
2. **Adopt W-SV-1's contrast half-widths as the provisional anchors for all three same-flight designs, with the
   estimand caveats.** Intent is 0.5093 at 1,080, from d = 8 discordant rows. SLU-F1 is 1.4866 at 1,080. Keep
   `same-flight-paired` unchanged. Re-anchor each design on its own first flown contrast: P-SV-1 or P-SV-2 for
   perception-variant, E4-1 for shadow-relisten.
3. **Record in the table source that the intent anchor depends on discordance.** A cell that expects mostly saves
   can justify a smaller effect with a stated d.

**Proposed diff (text only, not applied)** to `scripts/checks/stage3_effect_floor_check.py`:

```diff
@@ class Floor  (:230-243)
     source: str
     sampling: tuple[tuple[int, float], ...] = ()
+    #: Per-metric sampling anchors (``"intent"``, ``"slu_f1"``); when set, they
+    #: replace ``sampling`` for a declaration whose ``primary_metric_key`` names
+    #: the metric, and their MAX applies when the key is absent.
+    sampling_by_metric: tuple[tuple[str, tuple[tuple[int, float], ...]], ...] = ()
     bar: tuple[tuple[int, float], ...] = ()
@@ FLOOR_TABLE "same-flight-supply-variant"  (:262-275)
-            "instrument cell has flown and measured that null, the provisional floor "
-            f"anchor is {INSTRUMENT_NOTE} section 2a/2d row 2 (cell ROLL-AA, h_within "
-            "0.735 SLU / 0.000 intent at n = 200) -- same number as same-flight-paired, "
+            "measured by cell W-SV-1 (docs/results/2026-09-29-slurp-wsv1-fold-a-column-read.md; "
+            "knob/score-contrasts.json): the B-A CONTRAST CI95 half-width at n = 1,080, "
+            "intent 0.5093 (d = 8 discordant rows; discordance-driven) and pooled SLU-F1 "
+            "1.4866; the twin null (intent 0.000, SLU 0.5324) is the read's bar, not the floor -- "
             ...
-        sampling=((200, 0.735),),
+        sampling_by_metric=(("intent", ((1080, 0.5093),)), ("slu_f1", ((1080, 1.4866),))),
     ),
@@ FLOOR_TABLE "same-flight-perception-variant"  (:285-301)
-        sampling=((200, 0.735),),
+        # provisional: borrowed from W-SV-1 until P-SV-1/P-SV-2 measure their own contrast
+        sampling_by_metric=(("intent", ((1080, 0.5093),)), ("slu_f1", ((1080, 1.4866),))),
     ),
@@ FLOOR_TABLE "same-flight-shadow-relisten"  (:319-328)
-        sampling=((200, 0.735),),
+        # provisional: borrowed from W-SV-1 until E4-1 measures its own shadow contrast;
+        # intent is identical by construction, so only slu_f1 is anchored
+        sampling_by_metric=(("slu_f1", ((1080, 1.4866),)),),
     ),
```

**Companion changes the diff needs.** They are named here and not drafted:

- `floor_for(design, rows, *, purpose, metric=None)`.
- `_parse_declaration` reads an optional `primary_metric_key` from `intent` / `slu_f1`, and unknown values are
  refused.
- `accept.py` passes `metric="intent"` for the floor and `metric="slu_f1"` for the guard.
- Tests that pin the old anchor:
  - `tests/unit/test_stage3_effect_floor_check.py:192-196`, `:203-212`, `:220`, `:233-252`, `:260`
  - `tests/unit/test_e4_targeted_relisten.py:569-571`
- Docstring table row `:106`.
- Registration writers that restate 0.3163:
  - `scripts/flights/wsv1/write_slurp_wsv1_registration.py:60-61`, `:263`
  - `scripts/flights/e4/write_slurp_e4_registration.py:60-61`, `:264`, `:282`
  - `scripts/flights/w4sv/write_slurp_w4sv_registration.py:359`

**Cells the diff would affect.**

| cell | effect of the diff |
| --- | --- |
| `SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1` | new **blocking** `effect-below-floor` (0.79 < 1.4866 SLU). It is flying, so the finding is reported against bytes that are already committed. Rows are not re-registered; its read uses the in-flight twin bar. **Underpowered for 0.79.** |
| `SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1`, `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1`, `SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1`, `SAEA-SLURP-STAGE3-PSV2-FOLD-B-V1` | no finding (all declare `claims_benefit` false). Their stated `provisional_floor_pp` (0.3163 SLU / 0.0 intent) goes stale. P-SV-2's presence primary has no anchor under either table. |
| the five `-SMOKE-4-V1` cells | none (`form-proof`) |
| sealed-credit inner loop run 1 | nomination flips from `phase_supply.k` = 10 (**NOMINATED**) to **none**. `phase_supply.k` = 30 loses its guard discard. |

## What this note does not claim

This note makes no benefit, harm or nomination claim about any knob or cell. It does not change any registered
number, gate or read rule. It does not rule on whether W4-SV, E4-1, P-SV-1 or P-SV-2 should fly, stop or
re-register. The n = 200, 625 and 2,000 half-widths are sqrt(n) extrapolations from one flight and one knob
(d = 8), not measurements. They are development numbers on TRAIN Fold A (decision 28).
