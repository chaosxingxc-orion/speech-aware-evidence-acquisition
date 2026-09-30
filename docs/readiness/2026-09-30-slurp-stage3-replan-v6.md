# Stage-3 re-plan v6: the milestone flies, closure criterion C, and slot extraction as the main line (2026-09-30)

Author: Fable 5.1 (root coordinator; planning, decomposition, review); written down by the records agent. Supersedes
`docs/readiness/2026-09-30-slurp-stage3-replan-v5.md` (kept in place as the record, with a banner). Inputs: owner
decisions 207-209 of 2026-09-30 (registry `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`), the
result notes named beside each number, the consumption-module design
`docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md`, the E5 design and addenda
`docs/superpowers/specs/2026-09-29-e5-asr-tool-slot-value-verification-design.md`, and the direction note
`docs/readiness/2026-09-29-research-direction-system-level-v1.md`. Every number is a development number (decisions 28,
86) quoted from the file named beside it. Nothing here authorises a flight, a flip, a registration or an admission.

## 1. What decisions 207-209 settle

Owner (2026-09-30; the verbatim Chinese text is in registry rows 207-209; English translation):
"Decision 207: agreed; decision 208: agreed; decision 209: I feel the focus now should be slot extraction; go with
what you recommend."

1. **207 -- the milestone flies under one-shot semantics.** The successor allowance v2
   (`docs/receipts/owner/2026-09-30-slurp-test-sample-allowance-v2.json`) adds exactly the two zero-contact
   FIT ids (`SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-FIT-V1`, `...-MILESTONE-01-FIT-V1`), every other term
   unchanged; its sha256 is recorded by the signing commit. Package:
   `docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1/` (one attempt per read id, no smoke, no recovery, no
   re-read, no selection; `compacted_contacts` reported per arm per the prompt-fit ruling).
2. **208 -- P-SV-4 is authorised and flies after the milestone** (section 4).
3. **209 -- option C adopted, with the owner's emphasis.** SLURP closes at the measured structural ceiling of the
   current component set (Fold A on-list recall 92.1 %, rank-2/3 conversion 29.5 %;
   `docs/results/2026-09-30-slurp-intent-ceiling-under-current-components.md`), the module is carried to the other
   carriers under decision 196, and option B is explored. The owner's emphasis ("the focus should
   be slot extraction") makes B's SLOT half the main line (section 2); B's intent half (a new intent evidence kind) is
   not opened now.

**Closure criterion C, operationally (what "stable, replicated gain on the signed test sample" means today).**

- **The read.** MILESTONE-01 (COMP-1b) minus MILESTONE-00-PLAN (the v2.0 lock as flown), paired on the 3,010 records /
  682 prompts of `SLURP-TEST-SAMPLE-3010-V1`, official scorer `slurp-slu-official-test`, post-stratified inside the
  scorer with aggregates only (58 intent strata carried, `general_greet` closure-only; 10,000 draws, seed 20260929,
  prompt clusters resampled within strata), reported in natural-mixture and equal-stratum weightings, per intent and
  per scenario (`docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1/README.md`).
- **Primary metric as registered: INTENT** (`primary_metric_key: intent`, expected +4.6 re-declared from A2). The slot
  emphasis does not move it: the cell was registered before contact and cannot be re-declared. Official SLU-F1 is the
  non-inferiority guard at the FALLBACK null h_SLU 1.4492 (prompt-scaled; recording-scaled 0.7219 beside it); h_intent
  1.3329. No own null exists on the sample (`registered-facts-v1.json`, `own_null.kind` FALLBACK-SCALED-NOT-MEASURED).
- **"Gain":** the intent CI95 excludes zero on the post-stratified natural mixture AND the SLU-F1 guard holds.
- **"Replicated": NO RULE EXISTS.** Neither v5, the instrument note
  (`docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`), the milestone package nor the allowance
  defines a same-sign replicate of a milestone read. The allowance's spare read ids MILESTONE-02..05 are each "one
  composed system arm ... dev-admitted, read against MILESTONE-00-PLAN", and its `milestone_rule` forbids a second
  attempt or best-of on a consumed id. This is an **open item for the owner (decision 210)**; this plan does not
  invent the rule.

## 2. The slot-extraction programme (main line)

**Baseline taxonomy** (AGREE arm, TRAIN Fold A, `docs/results/2026-09-27-slurp-agree-arm-error-sources.md` section 3;
isolated oracle pp): MISSING 173 (9.80), SPURIOUS 253 (8.46; 183 on intent-right rows, 5.90), WRONG-TYPE 51 (4.63),
BOUNDARY 75 (2.88), WRONG-VALUE 41 (2.12), NEAR 56 (1.84), FORMAT 11 (0.39). Origin of the 407 delivered gold-side
errors: consumption 107, visible hearing 71, undetermined 229 -- of which 107 had the value in the supply
(`docs/results/2026-09-28-slurp-node-information-gain-ledger.md` section 2.3;
`docs/results/2026-09-29-slurp-slu-consumption-headroom-offline.md` section 3). A2 on DEV-2000-ADDED: entity TP 607 /
FP 481 / FN 420; 160 FP on 314 zero-gold rows, 140 of them emitting
(`docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md` section 4).

**Standing rules for every S round.** `primary_metric_key: slu` (official pooled SLU-F1), intent as the guard; no
registration without an offline prediction of at least 1.5 pp at a MEASURED conversion (decision 192); the same-flight
floor is SLU 1.49 at n = 1,080 (decision 190), cross-flight on DEV-2000-ADDED 2.5 pp with an in-chain A/A; any tool is
an offer the model may decline (206); empty results and slot = none are legal (199); every component lives in the one
module and must transfer (195, 196); SLURP-only GPU (187).

| # | round | GPU-h | read design | expected effect (source) | admission rule |
| --- | --- | --- | --- | --- | --- |
| S1 | SLU error-taxonomy refresh on the COMP-1b bytes: SPURIOUS / MISSING / WRONG-TYPE / BOUNDARY / NEAR / WRONG-VALUE / FORMAT counts, oracle pp, per slot type, the origin split (consumption / hearing / undetermined with the E1-E5 supply evidence), for A2 (DEV-2000-ADDED, sealed) and COMP-1b Fold A | 0 (model-free; gold offline through the governed loaders) | descriptive; reuses `scripts/analysis/slurp_slu_consumption_headroom.py` and the ledger's `derive_arm` | none claimed; it re-bases the 1.5 pp addressable counts (recover 25 FN or remove 50 FP at oracle 1.0; headroom note section 1) | none; it is the instrument that sets S2-S5's declared effects |
| S2 | Missing-slot proposal tool: a pinned transcript catalog OFFERED at the Solver's slot step; the Solver may decline; an empty result is legal. S2a offline design and oracle on COMP-1b bytes; S2b a stronger pinned ASR pass (tool contact, 0 core contacts); S2c the offer | S2a 0; S2b about 1 (estimate; one pass per fold); S2c about 3.5 (estimate; Fold A 1,080 at 1.60 GPU-h per 1,080 rows plus offered calls, `docs/results/2026-09-30-slurp-v2-1-lock-v1.md`) | same-flight Solver column if the module's columns reach the Solver node, else cross-flight on DEV with in-chain A/A (E5 addendum "Read form") | ceiling +8.21 [+6.95, +9.57] pp at perfect selection (113 items / 106 rows AGREE; 130 / 123 COMP-1b); cross-fit precision 0.2455 at a 10 % call rate; Whisper large-v3 containment 0.7513 < 0.80 (`docs/results/2026-09-30-slurp-e5-transcript-consistency-oracle-read.md`). Declared effect = ceiling x measured precision x conversion, never the ceiling | row 206 three-part gate (call-rate band, precision >= b + 0.10 and >= 2b with CI95 LB > b, conversion >= floor with CI95 LB > 0 and 0 intent rows differing); S2c registers only after S2a/S2b predict >= 1.5 pp |
| S3 | Slot-value knowledge: row-matched slot exemplars keyed by speech (M1, in the lock) vs the closed-list value vocabulary; target = the 163 errors whose value M1 printed and the Solver still missed (8.98 pp) | 0 until a candidate clears 192 | same-flight supply column (Solver) | M1 conversion 0.2471; vocabulary route 0.24 pp at W4's list rate (ceiling 4.60; closed types 0.73); W5 slot exemplars 0.15 (headroom note section 2) | W5 CLOSED by the coordinator under 192 (owner may reopen); rule cards CLOSED (191); nothing registrable today |
| S4 | Stage column / scope-rule line | 0 | offline stage column on sealed outputs | +0.49 [-0.01, +1.00] on A2, A/A +0.73 [+0.25, +1.23]; Fold A +1.35 shrank (`docs/results/2026-09-30-slurp-comp2-stage-column-dev2000-read.md`) | CLOSED as its own claim (FAILS Q2, bar 1.5485); REMAINS a registered no-harm deliver stage `saea-deliver-scope-rule-v1` (thresholds 0.8 / 5 fixed, no re-tune), re-read only as a column inside a composed read |
| S5 | SPURIOUS reduction with the empty-slot right: an explicit "no entities" option in the Solver contract (module step 6a, AT-M5) plus the N1 none signal (entity-free exemplar share >= 0.6, fixed before flight) -- the MODEL decides "no slot"; nothing is deleted by the system | 0 for 6a; about 2 for a same-flight supply-variant column (estimate) | same-flight supply-variant column beside the next contract arm | N1 on AGREE: oracle +0.68 [+0.28, +1.10], +0.17 at M1; under a forced-emission contract oracle +1.78 (`docs/results/2026-09-29-slurp-supply-abstention-headroom-offline.md` section 5); DEV A2: 51 rows trigger, 17 with entities (COMP-2 read) | under 1.5 today, alone or with S4 (+0.49); registers only if S1 finds a separable SPURIOUS mass; answer-side B4 stays closed unless recall cost < 0.22 exact per FP removed |

Order: S1 now (zero GPU, during the milestone); S2a and S5's step 6a in parallel after S1; S2b on the owner's pin
(decision 212); S2c or S5's column only after an offline prediction >= 1.5 pp is on file.

## 3. The module path

Module `saea-evidence-consumption-module-v1`, profile `slurp`, lock v2.1 (decision 204); step 6 DONE, harness `module`
switch class, first module cell HELD (`docs/readiness/2026-09-30-slurp-stage3-module-comp1b-dev2000-added-v1/`,
byte proof AT-M6; a flight is optional, about 3.4 GPU-h per its README).

| component | state |
| --- | --- |
| lock layer (M1 exemplars, slot store v2, normaliser v3, G5 Reviewer template) | on (lock) |
| `agree-vote-seed`, `centroid-boundary-key` (COMP-1b) | on (A2 admitted) |
| Solver citation contract | off (COMP-1 harm cause) |
| scope rule `saea-deliver-scope-rule-v1` (S4) | column only |
| `supply_abstain` + Solver "no entities" option (S5) | not built (step 6a); shadow/column first |
| missing-slot proposal offer (S2) | not built; enters as an offer read as a column |
| `key-source:k6p` (P-SV-4) | off until the DEV replicate (section 4) |
| core-native re-listen | off (SHADOW HARM, closed) |

**Carrier all-off arms (HELD).** Audio2Tool `a2t-native-stage3-module-alloff-v1` is request-identical to A2T-AA, so
its module null (h_A2T 1.625) is met by the byte proof without a flight. Earnings-21
`earnings21-native-stage3-module-alloff-v1` (1,593 rows, cap 4.0 GPU-h) needs a flight: its native-window module null
is unmeasured. Earnings-22 has no own null and no baseline fragment. Decision 187 reads "SLURP only until the owner
reopens the other carriers"; 209-C adopts the carry, and the coordinator reads the milestone seal as the point at which
the E21 all-off A/A may fly. Confirmation is asked as decision 211; component-on cells on any carrier still wait.
Status (Audio2Tool and Earnings-21 all-off cells): **HELD until SLURP lock (owner 2026-09-30)** -- decision 211.

## 4. P-SV-4 (the remaining intent item)

Cell `slurp-native-stage3-psv4-fold-b-v1`: K6p key-source Perception column, TRAIN Fold B, level-2, intent primary,
declared +1.1 pp vs floor 0.65 (inner-loop run 3 predicts +1.06;
`docs/results/2026-09-30-slurp-sealed-credit-inner-loop-run-3.md`); flies after the milestone, about 2.2 GPU-h
(estimate: 1.60 x 15/11 contacts; cap 16.4). **Replication rule on NOMINATED (v5):** a replicate on DEV-2000-ADDED
before `key-source:k6p` enters the module. A cross-flight DEV read cannot resolve +1.1 pp (A2's floor 2.598), so the
replicate must be the same-flight column form with the roster moved, same sign, CI95 excluding zero at the same-flight
floor -- form proposed as decision 213.

## 5. Coordinator checkpoints (script-run)

- Every launch: `flight_registration_check.py`, `cli check`, `stage3_effect_floor_check.py` (`primary_metric_key: slu`
  on every S cell), `finite_completion_policy_check.py`, `stage3_algorithm_label_check.py`, `handoff_freshness_check.py`.
- Milestone flip: allowance v2 sha in both fragments; preflip gate at zero refusals; decision 151's report named in the
  first countersignature; the read reports `context_fit.compacted_contacts` per arm.
- Any tool offer (S2): `tool_catalog_check.py` pins the wrapper; one function, one schema, Solver request only.
- Any module cell: `harness_admission_check.py` (rule 8), `module_equivalence_proof.py`, `engineering_base_check.py`.
- Before any S registration: the offline prediction file (>= 1.5 pp at a measured conversion) is named in the cell's
  `stage3_measurement` block (decision 192).

## 6. Decisions the owner will be asked for next

1. **210 -- what "replicated" means in closure criterion C.** Options: (a) the DEV replicate already on file (Fold A ->
   DEV-2000-ADDED, A2) plus one milestone read with intent CI95 excluding zero; (b) (a) plus a second sample read of the
   same arm under a spare id; (c) (a) plus the closure-roster read as the confirmation. Coordinator recommends **(a)**,
   with (c) as the final read: a second read of the same arm on the same rows measures decode variance, not
   replication.
2. **211 -- the E21 module all-off A/A flies once the milestone seals** (Audio2Tool needs no flight). Recommends
   **yes**; component-on carrier cells stay closed. **RULED 2026-09-30 (registry row 211): not at the milestone seal --
   lock SLURP first, then Audio2Tool and E21; decision 187 holds until the lock.**
3. **212 -- pin a stronger ASR tool for S2b** (a new pinned tool contact class, 0 core contacts) after S1 and S2a.
   Recommends **yes, conditional** on S2a predicting >= 1.5 pp on the contained subset at the measured precision.
4. **213 -- the P-SV-4 DEV replicate form** (same-flight column on DEV-2000-ADDED, same sign, CI95 excluding zero).
   Recommends **yes**.
