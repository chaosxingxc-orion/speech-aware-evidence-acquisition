# Cell P-SV-2 (phase-2 Perception branches, level 2): preregistration

Registered 2026-09-29 at study commit `f33e8a0f2`, before any contact, from the retained AGREE
arm fragments by script (decision 58) under owner decisions 184, 186 and 188. Development numbers only.

| item | value |
| --- | --- |
| base | the AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` re-targeted to TRAIN Fold B |
| program | `phase-native-candidates-review-revise-pbranch3-l2-v1` (ceiling 15, level 2, K = 3) |
| branches | `b-list3` (min_candidates 3), `t-twin` (twin), `a-agree` (delivering) |
| design / claim | `same-flight-perception-variant` / `nominated` |
| primary | gold-on-list (present) in the branch Perception note (primary, a presence measurement; coordinator ruling O4): B (min_candidates 3) minus A; official intent accuracy of the level-2 branch Solver column reported beside, never gating; gold rank and list size beside |
| expected effect | 0.0 pp, `claims_benefit` false; ceiling 49 rows = 4.54 pp on Fold A |
| rosters | tuning `SLURP-EVO-FOLD-A-V2`; read `SLURP-EVO-FOLD-B-V2` |
| runs | `SAEA-SLURP-STAGE3-PSV2-FOLD-B-V1` / `SAEA-SLURP-STAGE3-PSV2-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-PSV2-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-PSV2-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-PSV2-FOLD-B-BRANCH-READ-V1` |
| composed config hashes | arm `6dd791b7c2924d618643345c4e14fa4d7b3223f9d8fdcc903246b480c2b16048`; smoke `e2653674a2107ff579560bcbfac445991ef485a6d909e9e98f01d1d27eafdd13` |
| protocol hashes | arm `acde331034cae261a0c4af33ade84bfafdff57b7a8d78e90f52bb5e2d33788b3`; smoke `9ca9909a6b208fa278efcbb744b5bbc91f9f00ae07dc73463e4c25d738032bea` |
| split identity | arm `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`; smoke `bdd025a1f1c0a4a1ebd1b1204e7d3e781c3ae2543db7be324420f85171576e32` |

## Decision rule (fixed here)

SAME-FLIGHT PERCEPTION-BRANCH READ (owner decision 184; level 2; claim ceiling 'nominated', ruling O1). Per branch (a-agree delivering, b-list3, t-twin): the sealed branch note's candidate list gives gold's rank (1/2/3/absent), top1 and present offline (gold enters only offline); the branch's level-2 first-visit Solver answer is rendered through the delivered row's normaliser and projection and scored ONCE with slurp-slu-official-train (score_complete_derived_copy); A's column is A's own first Solver answer. Every contrast is a paired ROW bootstrap (cluster key sample_id, 10,000 draws, seed 20260929); the utterance-level number is reported beside and never gates. (1) THE TWIN NULL: T minus A per metric; the bar = |T - A offset| + its CI95 half-width, reported beside the provisional floor 0.3163 pp. (2) PRESENCE: b-list3 minus A on gold-on-list (present) in the branch note (primary, ruling O4). NOMINATED (as a presence change) iff the present CI95 lower bound is above zero AND the point delta exceeds the twin's present bar. Reported beside, never gating: official intent accuracy and SLU-F1 of the level-2 branch Solver column (B vs A vs T), list size, gold rank, and the conversion of gold at rank 3. A presence nomination opens no system claim: it only informs a later level-2 intent cell on the same pair.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-PSV2-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows (the committed prefix receipt) prove FORM and nothing else: the 15-ceiling pbranch3-l2 program loads, the Perception branches fan out at the one visit and the non-A branches take one first-visit Solver contact each, every branch fits its measured bound, the perception-branch receipt and I7v seal, and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-PSV2-FOLD-B-V1": {
      "aa_arm_id": "t-twin",
      "ceiling": {
        "pp": 4.54,
        "roster": "SLURP-EVO-FOLD-A-V2",
        "rows": 49,
        "what": "the 49 wrong rows with gold in the boundary block but off Perception's list on Fold A (4.54 pp presence ceiling); at the ledger's rank-3 conversion 12.0 % the delivered-intent ceiling is about 6 rows (about 0.5 pp), docs/results/2026-09-28-slurp-node-information-gain-ledger.md"
      },
      "claim": "nominated",
      "claims_benefit": false,
      "conversion_basis": "the presence gain of a forced three-candidate list and its conversion are UNMEASURED; spec section 6 notes only the 270 Fold A rows with lists of one (35) or two (235) can change (row 139: no prior, so the declaration is 0.0 nominated with the ceiling beside)",
      "expected_effect_pp": 0.0,
      "level": 2,
      "measurement_design": "same-flight-perception-variant",
      "note": "Phase-2 cell P-SV-2 (level 2, K = 3). Expected effect declared from the ledger's measured numbers: ceiling the 49 wrong rows with gold in the boundary block but off Perception's list on Fold A (4.54 pp presence ceiling); at the ledger's rank-3 conversion 12.0 % the delivered-intent ceiling is about 6 rows (about 0.5 pp), docs/results/2026-09-28-slurp-node-information-gain-ledger.md; conversion basis: the presence gain of a forced three-candidate list and its conversion are UNMEASURED; spec section 6 notes only the 270 Fold A rows with lists of one (35) or two (235) can change (row 139: no prior, so the declaration is 0.0 nominated with the ceiling beside). expected_effect_pp 0.0 sits below this design's provisional floor 0.3163 pp (0.735 x sqrt(200 / 1080), the ROLL-AA anchor the gate registers for same-flight-perception-variant), so claims_benefit is false; the read's bar is the twin (T) null measured in this flight, per metric |T - A offset| + its CI95 half-width. The delivered row is branch A: delivered intent and SLU are identical by construction at the request level (reported, never contrasted). Tuning roster TRAIN Fold A (the node ledger shaped the design), read roster TRAIN Fold B (ruling O2; owner decision 186: rollout-exposed only, no branch value built from Fold B rollouts).",
      "primary_metric": "gold-on-list (present) in the branch Perception note (primary, a presence measurement; coordinator ruling O4): B (min_candidates 3) minus A; official intent accuracy of the level-2 branch Solver column reported beside, never gating; gold rank and list size beside",
      "provisional_floor_pp": {
        "arithmetic": "0.735 * sqrt(200 / 1080) = 0.3163 pp (ROLL-AA anchor, provisional)",
        "intent_accuracy": 0.0,
        "slu_f1": 0.3163
      },
      "read_bar": "|twin offset| + twin CI95 half-width, per metric, measured in this flight (ruling O6: one twin)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 1080,
      "tuning_roster": "SLURP-EVO-FOLD-A-V2",
      "variant_cost": {
        "extra_audio_seconds": 12619.19,
        "extra_audio_seconds_per_row_mean": 11.6844,
        "extra_contacts_per_row": 4,
        "extra_perception_contacts_per_row": 2,
        "extra_solver_contacts_per_row": 2,
        "note": "K - 1 = 2 non-A branches (B and the twin T), each one Perception contact at the one Perception visit and one Solver contact at the first Solver visit (level 2); every contact re-sends the row's speech packet, so 2 x row audio per branch, 4 x the Fold B total 3154.797375 s per flight"
      }
    }
  }
}
```
