# Cell P-SV-4 (phase-2 Perception branches, level 2): preregistration

Registered 2026-09-30 at study commit `2df3fcf0d3e6797a98dc4b030e3caaf3f1811656`, before any contact, from the retained AGREE
arm fragments by script (decision 58) under owner decisions 184, 186 and 188. Development numbers only.

| item | value |
| --- | --- |
| base | the AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` re-targeted to TRAIN Fold B |
| program | `phase-native-candidates-review-revise-pbranch3-l2-v1` (ceiling 15, level 2, K = 3) |
| branches | `b-k6p` (key_source k6p (centred centroid key + centred Fold B speech queries; agreement unchanged)), `t-twin` (twin), `a-agree` (delivering) |
| design / claim | `same-flight-perception-variant` / `nominated` |
| primary | official intent accuracy of the level-2 branch Solver column (primary): B (key_source K6p: the centred centroid key and the centred Fold B speech queries, agreement unchanged) minus A, with gold-on-list (present) and gold rank in the branch note beside; guard SLU-F1 of the same column; the delivered row is A and identical by construction at the request level (reported, never contrasted) |
| expected effect | 1.1 pp, `claims_benefit` true; ceiling 26 rows = 2.41 pp on SLURP-EVO-FOLD-B-V2 |
| rosters | tuning `SLURP-EVO-FOLD-A-V2`; read `SLURP-EVO-FOLD-B-V2` |
| runs | `SAEA-SLURP-STAGE3-PSV4-FOLD-B-V1` / `SAEA-SLURP-STAGE3-PSV4-FOLD-B-FIT-V1`; `SAEA-SLURP-STAGE3-PSV4-FOLD-B-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-PSV4-FOLD-B-SMOKE-4-FIT-V1`; read `SAEA-SLURP-STAGE3-PSV4-FOLD-B-BRANCH-READ-V1` |
| composed config hashes | arm `02ed6409e04341152a11738eaafe4779d066769b3af09483d10e2577c0dc643a`; smoke `4cc3cdd03cc2922b39a8abe15539e0d1cd54fb5b5ac7de1bf872603e40d80fb0` |
| protocol hashes | arm `6e095615dd9a246219709d4345cc3bb08f593a5dd0c9edb6d25a92386074ae6b`; smoke `28acf048a58ccb4f906e10a1a9389ce3fd72d8ab1004667d20252832154794e6` |
| split identity | arm `4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a`; smoke `bdd025a1f1c0a4a1ebd1b1204e7d3e781c3ae2543db7be324420f85171576e32` |

## Decision rule (fixed here)

SAME-FLIGHT PERCEPTION-BRANCH READ (owner decision 184; level 2; claim ceiling 'nominated', ruling O1). Per branch (a-agree delivering, b-k6p, t-twin): the sealed branch note's candidate list gives gold's rank (1/2/3/absent), top1 and present offline (gold enters only offline); the branch's level-2 first-visit Solver answer is rendered through the delivered row's normaliser and projection and scored ONCE with slurp-slu-official-train (score_complete_derived_copy); A's column is A's own first Solver answer. Every contrast is a paired ROW bootstrap (cluster key sample_id, 10,000 draws, seed 20260929); the utterance-level number is reported beside and never gates. (1) THE TWIN NULL: T minus A per metric; the bar = |T - A offset| + its CI95 half-width, reported beside the design's own provisional floor per metric (owner decision 190; stage3_measurement.provisional_floor_pp -- intent 0.6500 pp, SLU 1.4900 pp). (2) THE CONTRAST: b-k6p (key_source K6p: the centred centroid key and the centred Fold B speech queries, agreement unchanged) minus A on the level-2 branch Solver column's official intent accuracy (primary). NOMINATED iff the intent CI95 lower bound is above zero AND the point delta exceeds the twin's intent bar AND the SLU-F1 CI95 lower bound of the same column is not below minus the twin's SLU bar (guard). BRANCH-LOCAL HARM iff the intent CI95 upper bound is below zero and the point magnitude exceeds the twin bar. Otherwise NOT NOMINATED. Reported beside, never gating: gold-on-list (present) and mean gold rank of the B note vs A and T, gold at supplied-block rank 1 (the note's mechanism: +26 rows expected on Fold B), the conversion P(correct | gold rank r in the branch note) against the ledger's 97.57 / 26.98 / 12.0 %, and the delivered row (identical by construction). A nomination sends the composed policy to a full-system cross-flight read against an in-chain A/A; it admits nothing.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-PSV4-FOLD-B-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four Fold B rows (the committed prefix receipt) prove FORM and nothing else: the 15-ceiling pbranch3-l2 program loads, the Perception branches fan out at the one visit and the non-A branches take one first-visit Solver contact each, every branch fits its measured bound, the perception-branch receipt and I7v seal, and the episode completes. Scored by no one, read by no one.",
      "primary_metric": "none (structural form only)",
      "read_roster": "SLURP-EVO-FOLD-B-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-PSV4-FOLD-B-V1": {
      "aa_arm_id": "t-twin",
      "ceiling": {
        "pp": 2.41,
        "roster": "SLURP-EVO-FOLD-B-V2",
        "rows": 26,
        "what": "the +26 net Fold B rows K6p lifts to boundary-block rank 1 over the centroid + agreement key (815 vs 789 of 1,080; Fold A +22, 845 vs 823), an offline model-free read of sealed vectors (docs/results/2026-09-30-slurp-retrieval-key-recall-offline.md), reproduced from the two pinned artifacts by scripts/analysis/slurp_k6p_artifact_proof.py (proof.json sha256 ad34e12f)"
      },
      "claim": "nominated",
      "claims_benefit": true,
      "conversion_basis": "implied intent +11.6 rows of 1,080 on Fold B (+11.5 on Fold A; +5.0 to +6.6 in each of the four utterance halves), the note's analogue: rows lifted to block rank 1 are assumed to convert like today's rank-1 rows (P-SV-1 a-agree's rank-conditional conversions on Fold B). expected_effect_pp 1.1 = 11.6 / 1,080 rounded. Presence cost -0.7 / +0.2 pp (Fold A / Fold B); against the description key the P-SV cells fly as A, the presence change is 0 / +14 rows, so the flown A is a stricter comparator than cent_agree on rank and a looser one on presence. Rows lifted may be harder than today's rank-1 rows: the declaration is a registered expectation, never a claim. DISCLOSURE: the key family was chosen offline over the sealed vectors of BOTH folds (15 families compared; K6p carries no tuned parameter beyond the flown weights, and its centring statistics come from the Fold-B-disjoint R01C roster), so TRAIN Fold B is not a clean held-out roster for the key CHOICE; the registered tuning roster stays Fold A, and Fold B is read only through this flight's own same-flight columns",
      "expected_effect_pp": 1.1,
      "level": 2,
      "measurement_design": "same-flight-perception-variant",
      "note": "Phase-2 cell P-SV-4 (level 2, K = 3). Expected effect declared from the recall note's measured numbers: ceiling the +26 net Fold B rows K6p lifts to boundary-block rank 1 over the centroid + agreement key (815 vs 789 of 1,080; Fold A +22, 845 vs 823), an offline model-free read of sealed vectors (docs/results/2026-09-30-slurp-retrieval-key-recall-offline.md), reproduced from the two pinned artifacts by scripts/analysis/slurp_k6p_artifact_proof.py (proof.json sha256 ad34e12f); conversion basis: implied intent +11.6 rows of 1,080 on Fold B (+11.5 on Fold A; +5.0 to +6.6 in each of the four utterance halves), the note's analogue: rows lifted to block rank 1 are assumed to convert like today's rank-1 rows (P-SV-1 a-agree's rank-conditional conversions on Fold B). expected_effect_pp 1.1 = 11.6 / 1,080 rounded. Presence cost -0.7 / +0.2 pp (Fold A / Fold B); against the description key the P-SV cells fly as A, the presence change is 0 / +14 rows, so the flown A is a stricter comparator than cent_agree on rank and a looser one on presence. Rows lifted may be harder than today's rank-1 rows: the declaration is a registered expectation, never a claim. DISCLOSURE: the key family was chosen offline over the sealed vectors of BOTH folds (15 families compared; K6p carries no tuned parameter beyond the flown weights, and its centring statistics come from the Fold-B-disjoint R01C roster), so TRAIN Fold B is not a clean held-out roster for the key CHOICE; the registered tuning roster stays Fold A, and Fold B is read only through this flight's own same-flight columns. expected_effect_pp 1.1 sits ABOVE this design's provisional intent floor 0.6500 pp (0.65 x sqrt(1080 / 1080), owner decision 190 anchor for same-flight-perception-variant) (a same-flight column, so the cross-flight floor does not apply), so claims_benefit is true -- at about 1.7 x the floor, knowingly near it (the note's own caveat); the read's bar is the twin (T) null measured in this flight, per metric |T - A offset| + its CI95 half-width. The delivered row is branch A: delivered intent and SLU are identical by construction at the request level (reported, never contrasted). Tuning roster TRAIN Fold A (the node ledger shaped the design), read roster TRAIN Fold B (ruling O2; owner decision 186: rollout-exposed only, no branch value built from Fold B rollouts).",
      "primary_metric": "official intent accuracy of the level-2 branch Solver column (primary): B (key_source K6p: the centred centroid key and the centred Fold B speech queries, agreement unchanged) minus A, with gold-on-list (present) and gold rank in the branch note beside; guard SLU-F1 of the same column; the delivered row is A and identical by construction at the request level (reported, never contrasted)",
      "primary_metric_key": "intent",
      "provisional_floor_pp": {
        "arithmetic": "intent 0.65 * sqrt(1080 / 1080) = 0.6500 pp (primary; owner decision 190 anchor), SLU 1.49 * sqrt(1080 / 1080) = 1.4900 pp (guard reference)",
        "intent_accuracy": 0.65,
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
