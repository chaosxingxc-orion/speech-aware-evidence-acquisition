# Cell P-SV-1 (phase-2 Perception branches, level 2): preregistration

Registered 2026-09-29 at study commit `f33e8a0f2`, before any contact, from the retained AGREE
arm fragments by script (decision 58) under owner decisions 184, 186 and 188. Development numbers only.

| item | value |
| --- | --- |
| base | the AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` re-targeted to TRAIN Fold B |
| program | `phase-native-candidates-review-revise-pbranch3-l2-v1` (ceiling 15, level 2, K = 3) |
| branches | `b-top2contrast` (presentation_id top2-contrast-v1), `t-twin` (twin), `a-agree` (delivering) |
| design / claim | `same-flight-perception-variant` / `nominated` |
| primary | official intent accuracy of the level-2 branch Solver column (primary): B (top2-contrast-v1) minus A, with gold-on-list and gold rank in the branch note beside; guard SLU-F1 of the same column; the delivered row is A and identical by construction at the request level (reported, never contrasted) |
| expected effect | 0.0 pp, `claims_benefit` false; ceiling 42 rows = 3.89 pp on Fold A |
| rosters | tuning `SLURP-EVO-FOLD-A-V2`; read `SLURP-EVO-FOLD-B-V2` |
| runs | `SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1` / `SAEA-SLURP-STAGE3-PSV1-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-PSV1-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-PSV1-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-PSV1-FOLD-B-BRANCH-READ-V1` |
| composed config hashes | arm `969050e12caf63c151d4019dfcff6cd537d74b39c41107a931323c4a0f93e4d4`; smoke `1a77b38c55ca848de18cae6b3b32736ee2165d21a282480b36f4898798bae7bf` |
| protocol hashes | arm `2b550afb78f48c8085e3eebd4994a8dfea89b301268037f64ed235c7fba1d4de`; smoke `dc6a44c9ec54ad93ada200eab7878ab93fc89667b032dac5a52ba4b47c3c2339` |
| split identity | arm `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`; smoke `bdd025a1f1c0a4a1ebd1b1204e7d3e781c3ae2543db7be324420f85171576e32` |

## Decision rule (fixed here)

SAME-FLIGHT PERCEPTION-BRANCH READ (owner decision 184; level 2; claim ceiling 'nominated', ruling O1). Per branch (a-agree delivering, b-top2contrast, t-twin): the sealed branch note's candidate list gives gold's rank (1/2/3/absent), top1 and present offline (gold enters only offline); the branch's level-2 first-visit Solver answer is rendered through the delivered row's normaliser and projection and scored ONCE with slurp-slu-official-train (score_complete_derived_copy); A's column is A's own first Solver answer. Every contrast is a paired ROW bootstrap (cluster key sample_id, 10,000 draws, seed 20260929); the utterance-level number is reported beside and never gates. (1) THE TWIN NULL: T minus A per metric; the bar = |T - A offset| + its CI95 half-width, reported beside the provisional floor 0.3163 pp. (2) THE CONTRAST: b-top2contrast minus A on the level-2 branch Solver column's official intent accuracy (primary). NOMINATED iff the intent CI95 lower bound is above zero AND the point delta exceeds the twin's intent bar AND the SLU-F1 CI95 lower bound of the same column is not below minus the twin's SLU bar (guard). BRANCH-LOCAL HARM iff the intent CI95 upper bound is below zero and the point magnitude exceeds the twin bar. Otherwise NOT NOMINATED. Reported beside, never gating: gold-on-list and mean gold rank of the B note vs A and T, the conversion P(correct | gold rank r in the branch note) against the ledger's 97.57 / 26.98 / 12.0 %, the rows where top2-contrast-v1 rendered nothing (presentation_skip_reason, ruling O5), and the delivered row (identical by construction). A nomination sends the composed policy to a full-system cross-flight read against an in-chain A/A; it admits nothing.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-PSV1-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows (the committed prefix receipt) prove FORM and nothing else: the 15-ceiling pbranch3-l2 program loads, the Perception branches fan out at the one visit and the non-A branches take one first-visit Solver contact each, every branch fits its measured bound, the perception-branch receipt and I7v seal, and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1": {
      "aa_arm_id": "t-twin",
      "ceiling": {
        "pp": 3.89,
        "roster": "SLURP-EVO-FOLD-A-V2",
        "rows": 42,
        "what": "the 42 wrong delivered rows with gold at Perception rank 2 on Fold A (3.89 pp of 1,080; 63 rank-2 rows overall, 5.83 pp level-1 top1 ceiling), docs/results/2026-09-28-slurp-node-information-gain-ledger.md"
      },
      "claim": "nominated",
      "claims_benefit": false,
      "conversion_basis": "rank-2 -> rank-1 promotion rate under a top-2 contrast is UNMEASURED; the node ledger's conversion of gold at Perception rank 2 is 26.98 % and at rank 1 97.57 % (row 139: no prior, so the declaration is 0.0 nominated with the ceiling beside)",
      "expected_effect_pp": 0.0,
      "level": 2,
      "measurement_design": "same-flight-perception-variant",
      "note": "Phase-2 cell P-SV-1 (level 2, K = 3). Expected effect declared from the ledger's measured numbers: ceiling the 42 wrong delivered rows with gold at Perception rank 2 on Fold A (3.89 pp of 1,080; 63 rank-2 rows overall, 5.83 pp level-1 top1 ceiling), docs/results/2026-09-28-slurp-node-information-gain-ledger.md; conversion basis: rank-2 -> rank-1 promotion rate under a top-2 contrast is UNMEASURED; the node ledger's conversion of gold at Perception rank 2 is 26.98 % and at rank 1 97.57 % (row 139: no prior, so the declaration is 0.0 nominated with the ceiling beside). expected_effect_pp 0.0 sits below this design's provisional floor 0.3163 pp (0.735 x sqrt(200 / 1080), the ROLL-AA anchor the gate registers for same-flight-perception-variant), so claims_benefit is false; the read's bar is the twin (T) null measured in this flight, per metric |T - A offset| + its CI95 half-width. The delivered row is branch A: delivered intent and SLU are identical by construction at the request level (reported, never contrasted). Tuning roster TRAIN Fold A (the node ledger shaped the design), read roster TRAIN Fold B (ruling O2; owner decision 186: rollout-exposed only, no branch value built from Fold B rollouts).",
      "primary_metric": "official intent accuracy of the level-2 branch Solver column (primary): B (top2-contrast-v1) minus A, with gold-on-list and gold rank in the branch note beside; guard SLU-F1 of the same column; the delivered row is A and identical by construction at the request level (reported, never contrasted)",
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
