# Cell P-SV-3 (phase-2 Perception branches, level 2): preregistration

Registered 2026-09-29 at study commit `0b50d47e51abecc41ca92f197c1324642d719a6d`, before any contact, from the retained AGREE
arm fragments by script (decision 58) under owner decisions 184, 186 and 188. Development numbers only.

| item | value |
| --- | --- |
| base | the AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` re-targeted to TRAIN Fold B |
| program | `phase-native-candidates-review-revise-pbranch3-l2-v1` (ceiling 15, level 2, K = 3) |
| branches | `b-depth` (fuse_coverage {'m': 12, 'top_l': 12}), `t-twin` (twin), `a-agree` (delivering) |
| design / claim | `same-flight-perception-variant` / `nominated` |
| primary | gold-on-list (present) in the branch Perception note (primary, a presence measurement; owner decision 190's ruling-O4 framing extended to this axis): B (fuse_coverage.m and fuse_coverage.top_l raised together 8 -> 12, c unchanged at 1 -- the boundary-supply DEPTH itself, the inner loop's 'boundary_phase_supply +1 step') minus A; official intent accuracy of the level-2 branch Solver column reported beside, never gating; gold rank and list size beside |
| expected effect | 0.0 pp, `claims_benefit` false; ceiling 83 rows = 7.69 pp on Fold A |
| rosters | tuning `SLURP-EVO-FOLD-A-V2`; read `SLURP-EVO-FOLD-B-V2` |
| runs | `SAEA-SLURP-STAGE3-PSV3-FOLD-B-V1` / `SAEA-SLURP-STAGE3-PSV3-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-PSV3-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-PSV3-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-PSV3-FOLD-B-BRANCH-READ-V1` |
| composed config hashes | arm `2cf26125cd794ad3b7bced388ea9634264b56e81f1848521a3e1d2a2cb203738`; smoke `fc405b30ef8f76d0dea301f43a115702cfea34131cd0f684e939e87e6e711faf` |
| protocol hashes | arm `96d6e080344f5a1fa8cafdd45361685b3d8a3643165c9ff8b19377e7177cbe36`; smoke `3a819a6396f6d1228f13a09c37daa75dc7e23e171770b448f35f4b4714f97850` |
| split identity | arm `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`; smoke `bdd025a1f1c0a4a1ebd1b1204e7d3e781c3ae2543db7be324420f85171576e32` |

## Decision rule (fixed here)

SAME-FLIGHT PERCEPTION-BRANCH READ (owner decision 184; level 2; claim ceiling 'nominated', ruling O1). Per branch (a-agree delivering, b-depth, t-twin): the sealed branch note's candidate list gives gold's rank (1/2/3/absent), top1 and present offline (gold enters only offline); the branch's level-2 first-visit Solver answer is rendered through the delivered row's normaliser and projection and scored ONCE with slurp-slu-official-train (score_complete_derived_copy); A's column is A's own first Solver answer. Every contrast is a paired ROW bootstrap (cluster key sample_id, 10,000 draws, seed 20260929); the utterance-level number is reported beside and never gates. (1) THE TWIN NULL: T minus A per metric; the bar = |T - A offset| + its CI95 half-width, reported beside the design's own provisional floor per metric (owner decision 190; stage3_measurement.provisional_floor_pp -- intent 0.6500 pp, SLU 1.4900 pp). (2) PRESENCE: b-depth minus A on gold-on-list (present) in the branch note (primary, ruling O4). NOMINATED (as a presence change) iff the present CI95 lower bound is above zero AND the point delta exceeds the twin's present bar. Reported beside, never gating: official intent accuracy and SLU-F1 of the level-2 branch Solver column (B vs A vs T), list size, gold rank, and the conversion of gold at rank 3. A presence nomination opens no system claim: it only informs a later level-2 intent cell on the same pair.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-PSV3-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows (the committed prefix receipt) prove FORM and nothing else: the 15-ceiling pbranch3-l2 program loads, the Perception branches fan out at the one visit and the non-A branches take one first-visit Solver contact each, every branch fits its measured bound, the perception-branch receipt and I7v seal, and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-PSV3-FOLD-B-V1": {
      "aa_arm_id": "t-twin",
      "ceiling": {
        "pp": 7.69,
        "roster": "SLURP-EVO-FOLD-A-V2",
        "rows": 83,
        "what": "the 83 wrong rows with gold off Perception's list on Fold A entirely (7.69 pp presence ceiling): 49 of them still inside the retrieved boundary block but off the rendered list, 34 outside the block entirely, docs/results/2026-09-28-slurp-node-information-gain-ledger.md"
      },
      "claim": "nominated",
      "claims_benefit": false,
      "conversion_basis": "no conversion is claimed: raising the boundary-supply depth (fuse_coverage.m and fuse_coverage.top_l together, 8 -> 12, c unchanged) only changes what Perception is SHOWN, never the response contract or the presentation it renders from that supply; whether a newly shown item reaches top-1, appears on the note's candidate list, or changes the level-2 Solver's answer is UNMEASURED (row 139: no prior, so the declaration is 0.0 nominated with the ceiling beside)",
      "expected_effect_pp": 0.0,
      "level": 2,
      "measurement_design": "same-flight-perception-variant",
      "note": "Phase-2 cell P-SV-3 (level 2, K = 3). Expected effect declared from the ledger's measured numbers: ceiling the 83 wrong rows with gold off Perception's list on Fold A entirely (7.69 pp presence ceiling): 49 of them still inside the retrieved boundary block but off the rendered list, 34 outside the block entirely, docs/results/2026-09-28-slurp-node-information-gain-ledger.md; conversion basis: no conversion is claimed: raising the boundary-supply depth (fuse_coverage.m and fuse_coverage.top_l together, 8 -> 12, c unchanged) only changes what Perception is SHOWN, never the response contract or the presentation it renders from that supply; whether a newly shown item reaches top-1, appears on the note's candidate list, or changes the level-2 Solver's answer is UNMEASURED (row 139: no prior, so the declaration is 0.0 nominated with the ceiling beside). expected_effect_pp 0.0 sits below this design's primary_metric_key 'present': gold-on-list carries no numeric floor under owner decision 190 (or the table it superseded); reported, never checked against a bound, so claims_benefit is false; the read's bar is the twin (T) null measured in this flight, per metric |T - A offset| + its CI95 half-width. The delivered row is branch A: delivered intent and SLU are identical by construction at the request level (reported, never contrasted). Tuning roster TRAIN Fold A (the node ledger shaped the design), read roster TRAIN Fold B (ruling O2; owner decision 186: rollout-exposed only, no branch value built from Fold B rollouts).",
      "primary_metric": "gold-on-list (present) in the branch Perception note (primary, a presence measurement; owner decision 190's ruling-O4 framing extended to this axis): B (fuse_coverage.m and fuse_coverage.top_l raised together 8 -> 12, c unchanged at 1 -- the boundary-supply DEPTH itself, the inner loop's 'boundary_phase_supply +1 step') minus A; official intent accuracy of the level-2 branch Solver column reported beside, never gating; gold rank and list size beside",
      "primary_metric_key": "present",
      "provisional_floor_pp": {
        "arithmetic": "primary_metric_key 'present' (gold-on-list) carries no numeric floor under owner decision 190; intent and SLU are reported beside, never gating this cell",
        "intent_accuracy": 0.65,
        "present": null,
        "slu_f1": 1.49
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
