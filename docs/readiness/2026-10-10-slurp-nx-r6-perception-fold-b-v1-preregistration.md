# Cell NX-R6-PERCEPTION (node-extreme programme round R6-P1, Perception template column): preregistration

Registered 2026-10-10 at study commit `fc0c0fc14a3b080e04752618188d798628471a76`, before any contact, by script (decision 58) from the P-SV-4 Fold B fragments and the consumption-module compiler under the NX programme (owner decisions 245-248). Development numbers only.

| item | value |
| --- | --- |
| base | the COMP-1b composition as a module block on lock v2.2 (agree-vote-seed + centroid-boundary-key ON; v4g at delivery), Reviewer loop OFF, no tool schema on any role |
| program | `phase-native-module-v1-c10` (ceiling 10 = 2 + 2 x (5 - 1)) |
| arms | `p1`, `p2`, `p3` (candidates, pinned under `configs/probes/nx/perception/r6/`), `aa` (twin of `lock`), `lock` (delivering, `configs/probes/slurp_native_role_perception_v3.txt`) |
| design / claim | `same-flight-node-column` / `nominated`; a MEASUREMENT cell, `claims_benefit` false |
| primary | node-local: rank-1 E=none against empty gold (AUC, precision, recall) and the information gain over {N1, intent prior}; guards: the paired Perception note metrics and the level-2 Solver column |
| expected effect | 0.75 pp (the design's gate estimate, range 0.75 .. 0.98), `claims_benefit` false; provisional floor SLU 1.49 pp |
| rosters | tuning `SLURP-EVO-FOLD-A-V2`; read `SLURP-EVO-FOLD-B-V2` (selection read; see the disclosure) |
| runs | `SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-V1` / `SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-COLUMN-READ-V1` |
| composed config hashes | arm `dae31324906bdae2dd076bad0c267e6e079993b556abfe5246354e056ebe8c68`; smoke `7ca216808fd38765f2862bb9fdd583312fc89b10642bbe0fbf3875efdb84d208` |
| protocol hashes | arm `894b63c4f10cf66814f978498cef7ef0422fc84307e09e6893f202430bbac870`; smoke `356cd43ec8c546b03c040126df6752dd67176fee340ed4a32a2a8aeda068de69` |
| split identity | arm `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`; smoke `bdd025a1f1c0a4a1ebd1b1204e7d3e781c3ae2543db7be324420f85171576e32` |

## Smoke recovery (the cell's single recovery re-registration)

The predecessor attempt made its 20 Perception contacts (4 rows x 5 arms) and stopped when the first level-2 Solver input was built: the level-2 branch view in rails/runner.py replaced the Perception state's content with the branch's note without rebinding source_response_sha256, so SlurpIntentHypothesisError ('hypothesis content does not match its source response SHA-256') fired. Root cause fixed by the level-2 note source-hash binding fix (rails/runner.py; commit named at merge). The smoke is re-flown whole under the rec1 attempt ids; the arm is untouched.

RECOVERY 2026-10-10 (the cell's single one; coordinator brief, Fable 5.1). The generation budget is run-cumulative across the attempts of the run id (core/model/adapter.py), so the rec1 plan carries the original plan plus the failed attempt's realised spend: planned_model_calls 40 + 20 = 60 and planned_speech_audio_seconds ceil(102 + 50.908) = 153 (gpu hours unchanged, 1.0). The FIT cap is structural and unchanged: rows x max_contacts x (max_speech_packets + 3) = 4 x 10 x 4 = 160; the FIT attempt id also takes the rec1 suffix because a (run_id, attempt_id) pair is a one-time key and the failed FIT attempt was opened. The Perception arm, its attempt ids, its caps and its template pins are untouched. The smoke plans therefore carry run-cumulative budgets of 60 model calls / 153 speech-seconds (the failed attempt spent 20 / 50.908; the rec1 attempt is budgeted 40 / 102); the FIT endpoint cap is structural, not run-cumulative (160 = 4 rows x 10 contacts x 4 endpoints). The arm's budgets and attempt ids are unchanged: arm 10,800 model calls, FIT cap 43,200. At most one recovery re-registration per cell: a second failure closes the cell.

## Decision rule (fixed here)

SAME-FLIGHT PERCEPTION TEMPLATE COLUMN READ (NX programme round R6-P1; owner decisions 245-248; instrument E1/E2 at the Perception node; claim ceiling 'nominated'; a MEASUREMENT cell that claims no benefit). One flight, one Perception visit per row, five arms over the SAME QueryState and evidence: p1 (E= presence tag), p2 (E= tag + up to three M= heard mentions), p3 (E= tag with an unsure hedge + mentions), aa (the twin, replicate_of lock) and lock (the locked template, delivering, last); each non-delivering arm is followed by its own first-visit Solver contact (the LOCKED Solver template) over its own note. THE READS, all from this one flight's sealed columns, model-free (scripts/analysis/nx_r6_read.sh): (1) NODE-LOCAL (reader E2b, scripts/analysis/slurp_nx_perception_column_read.py, tag grammar configs/probes/nx/perception/r6/TAG-GRAMMAR-v1.md, p3 read with --tag-set p3=none,some,unsure): per arm, on the rank-1 candidate and on the list majority, the parse classes (ok / absent / invalid), E=none AUC / precision / recall against empty gold, E=some precision / recall against non-empty gold, the unsure rate by gold class, heard-mention containment (share of gold entities whose normalised surface equals an offered M= surface, per slot type) and option precision; the paired intent guards against lock (gold on list, rank-1 share, candidate count, prompt tokens, note parse status); whole-utterance cluster bootstrap CI95, 10,000 draws, seed 20260915. (2) INFORMATION GAIN and the GATE ESTIMATE per candidate arm (scripts/analysis/slurp_nx_r6_upstream_empty.py --verdict-source perception-arm:<arm> --gain-baseline {n1,n1+prior,n1+prior+lock}): the cross-fitted AUC increment of the rank-1 E=none verdict over the baseline for 'gold empty' with a whole-utterance cluster bootstrap CI95 (2,000 draws, seed 20261010), and the delivered-metric estimate of the c3verdict-style gate (verdict E=none AND N1 >= 0.2, plus the fixed N1 grid) on the lock Solver column of the v4g base (10,000 draws, seed 20260915): pp with CI95, false fills removed, non-empty exact lost, intent rows moved. (3) LOCKED-CONSUMER read: each arm's own level-2 Solver column against lock's (the E2 Solver reader inside the node-local pass, and the official pooled SLU-F1 of each column scored once with slurp-slu-official-train and read paired per row). (4) THE TWIN NULL: aa minus lock on every metric, read first. ACCEPTANCE (design sections 2.2 and 4, decision 247): NODE-LOCAL acceptance of an arm = rank-1 E=none recall >= 0.80 and precision >= 0.75 on empty-gold rows, with a rank-1 tag parse rate (ok) >= 0.90 (below that the arm is reported as a FORM FAILURE, not a verdict), and no intent guard moving by more than the twin's own movement plus 0.65 pp; INFORMATION GAIN = the CI95 lower bound of the cross-fitted AUC increment over {N1, intent prior} above zero (additional) -- stability (the same sign and CI-LB > 0 on TRAIN Fold A with the rule fixed on Fold B) is R6-A's term, not this cell's; the delivered-metric estimate is reported through the measured exchange rates (+0.033 pp per false fill removed, -0.070 pp per non-empty exact row lost), with intent rows moved = 0. NOTHING IS LOCKED HERE: this is a selection read on the selection roster. PLATEAU RULE: two evaluated Perception-entity rounds without an arm clearing node-local acceptance close the node; the next lever is then the v2 note contract (decision 248) or the supply-side presence prior, in that order.

## Tuning disclosure

the three Perception templates' mechanism hypotheses and the N1 >= 0.2 gate of the delivered-metric estimate were derived from AGGREGATE tables of docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md, which were computed on TRAIN Fold B (the NX R1 flights' columns), this cell's read roster; no utterance text, gold value or note body was read to author them. Fold B is the selection roster of the design (docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md section 2.3: Fold B selects, Fold A confirms, DEV-2000-ADDED composes), so the read here is a selection read and every number is descriptive until the Fold A confirmation (R6-A) fixes the rule.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows (the committed prefix receipt) prove FORM and nothing else: the phase-native-module-v1-c10 program loads, the five Perception template arms fan out at the one Perception visit, each non-delivering arm takes its own level-2 Solver contact, every arm fits its estimated bound, the arm receipt (saea-perception-branch-arms-v4) and I7v seal, and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-V1": {
      "aa_arm_id": "aa",
      "ceiling": {
        "pp": 0.75,
        "roster": "SLURP-EVO-FOLD-B-V2",
        "rows": 27,
        "what": "the 27 false fills the N1-gated Solver-side verdict removes on Fold B iteration 1 at 0.033 pp each, less 3 non-empty exact rows at 0.070 pp each (+0.68 predicted, +0.75 measured); range +0.75 .. +0.98 pp"
      },
      "claim": "nominated",
      "claims_benefit": false,
      "conversion_basis": "Declared expectation +0.75 pp official pooled SLU-F1 (range +0.75 .. +0.98) = the design's gate estimate (docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md section 2.2): the c3verdict rule with the verdict source swapped from the Solver-side aggressive arm to the Perception arm's rank-1 E=none, gated by N1 >= 0.2, on the lock Solver column of the v4g base. It is measured only for the Solver-side verdict (docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md section 4: +0.75 [+0.27, +1.24] on iteration 1 and +0.98 [+0.50, +1.48] on iteration 2, 0 intent rows moved, false fill 91 -> 64 and 93 -> 60, 3 non-empty exact rows lost per flight; recall 0.81-0.83 and precision 0.74-0.76 on empty-gold rows) and is conditional on the Perception verdict matching that quality; if it only mirrors N1 the gain is about +0.13 pp (the deterministic gate alone). Exchange arithmetic on the iteration-1 point: 27 false fills x 0.033 = +0.89 and 3 exact rows x -0.070 = -0.21, +0.68 predicted against +0.75 measured. THIS IS A MEASUREMENT CELL under decisions 245/247: it claims NO benefit (claims_benefit false), because +0.75 sits under both the 1.49 pp same-flight floor and the 1.5 pp registration bar of decision 192; it is judged on its node metric and its information gain, and its delivered-metric effect is estimated offline from its own sealed columns before any cascade cell is registered.",
      "expected_effect_pp": 0.75,
      "measurement_design": "same-flight-node-column",
      "note": "NX round R6-P1 (level: Perception node column, K = 5 Perception template arms, level-2 Solver columns). A MEASUREMENT cell under decisions 245/247 (design docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md section 2.2). Declared expectation +0.75 pp official pooled SLU-F1 (range +0.75 .. +0.98) = the design's gate estimate (docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md section 2.2): the c3verdict rule with the verdict source swapped from the Solver-side aggressive arm to the Perception arm's rank-1 E=none, gated by N1 >= 0.2, on the lock Solver column of the v4g base. It is measured only for the Solver-side verdict (docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md section 4: +0.75 [+0.27, +1.24] on iteration 1 and +0.98 [+0.50, +1.48] on iteration 2, 0 intent rows moved, false fill 91 -> 64 and 93 -> 60, 3 non-empty exact rows lost per flight; recall 0.81-0.83 and precision 0.74-0.76 on empty-gold rows) and is conditional on the Perception verdict matching that quality; if it only mirrors N1 the gain is about +0.13 pp (the deterministic gate alone). Exchange arithmetic on the iteration-1 point: 27 false fills x 0.033 = +0.89 and 3 exact rows x -0.070 = -0.21, +0.68 predicted against +0.75 measured. THIS IS A MEASUREMENT CELL under decisions 245/247: it claims NO benefit (claims_benefit false), because +0.75 sits under both the 1.49 pp same-flight floor and the 1.5 pp registration bar of decision 192; it is judged on its node metric and its information gain, and its delivered-metric effect is estimated offline from its own sealed columns before any cascade cell is registered. Provisional floor SLU 1.49 pp (1.49 x sqrt(1080/1080), borrowed from same-flight-supply-variant per the instrument README until a node-column cell measures its own twin null; the R1 flights have flown but their official-score twin null is a Solver-node null), so expected_effect_pp 0.75 sits at about 0.5 x the floor, knowingly under it: the cell looks for a NODE metric and an information gain, not for a delivered effect. The delivered row is the lock arm: delivered intent and SLU are identical by construction at the request level (invariant I7; reported, never contrasted). Tuning roster TRAIN Fold A; read roster TRAIN Fold B (a selection read). DISCLOSURE: the three Perception templates' mechanism hypotheses and the N1 >= 0.2 gate of the delivered-metric estimate were derived from AGGREGATE tables of docs/results/2026-10-10-slurp-nx-r6-upstream-empty-decision-offline.md, which were computed on TRAIN Fold B (the NX R1 flights' columns), this cell's read roster; no utterance text, gold value or note body was read to author them. Fold B is the selection roster of the design (docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md section 2.3: Fold B selects, Fold A confirms, DEV-2000-ADDED composes), so the read here is a selection read and every number is descriptive until the Fold A confirmation (R6-A) fixes the rule.",
      "primary_metric": "node-local: rank-1 E=none against empty gold on the arm's sealed Perception notes (AUC, precision, recall; reader E2b), with the cross-fitted AUC increment over {N1, intent prior} (information gain) and the gate estimate of the delivered SLU-F1 (offline, lock Solver column, v4g base); guards: gold-on-list, rank-1 share, candidate count, prompt tokens, note parse status and the level-2 Solver column's official intent paired against lock (rows differing <= 7 = 0.65 pp of 1,080)",
      "primary_metric_key": "slu",
      "provisional_floor_pp": {
        "arithmetic": "SLU 1.49 * sqrt(1080 / 1080) = 1.4900 pp, intent 0.65 * sqrt(1080 / 1080) = 0.6500 pp (guard)",
        "intent_accuracy": 0.65,
        "slu_f1": 1.49
      },
      "read_bar": "|aa twin offset| + twin CI95 half-width, per metric, measured in this flight",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 1080,
      "template_variants": {
        "candidate_arms": 3,
        "node": "perception",
        "twin": true
      },
      "tuning_roster": "SLURP-EVO-FOLD-A-V2",
      "variant_cost": {
        "extra_audio_seconds": 25238.38,
        "extra_audio_seconds_per_row_mean": 23.3689,
        "extra_contacts_per_row": 4,
        "extra_perception_contacts_per_row": 4,
        "extra_solver_contacts_per_row": 4,
        "note": "K - 1 = 4 non-delivering arms (three candidates and the twin), each one Perception contact AND one level-2 Solver contact at the one Perception visit; every contact re-sends the row's speech packet, so 8 x the Fold B total 3154.797375 s per flight (review-off base: 2 contacts per row, ceiling 10 = 2 + 2 (K - 1))"
      }
    }
  }
}
```
