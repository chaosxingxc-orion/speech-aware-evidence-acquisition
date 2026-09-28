# The knowledge wave's shared in-chain A/A: preregistration

Registered 2026-09-27 at study commit `df8ccf9ceb40b8f63cf2d927e9ba0ca93bc86186`, before any contact, from the retained AGREE
fragments by script (`scripts/flights/wave/derive_slurp_wave_aa_cell.py`, decision 58), under owner decisions 160, 161 and 164. Development numbers only
(owner decisions 28 and 86); never a test claim.

| item | value |
| --- | --- |
| base | the retained AGREE arm `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (intent 85.8333 / SLU 65.1575), sealed, never re-flown |
| factor | none: the AGREE arm's own bytes |
| readers | W1 SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1 (read SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1); W3 SAEA-SLURP-STAGE3-W3-FOLD-A-V1 (read SAEA-SLURP-STAGE3-W3-FOLD-A-PAIRED-ANALYSIS-V1); W4 SAEA-SLURP-STAGE3-W4-FOLD-A-V1 (read SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1) |
| runs | `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` / `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-FIT-V1`; READ `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-PAIRED-READ-V1` |
| composed config hash | `e2d3a3ebad30c52bbeac70ca696dafdfc2efa8de38187d378df70592c8b1327c` |
| protocol hash | `41b57642c0bc196afcdc88ddc6747fd2a2b4d0fcda6ea3e53bc8542ac7f54917` |
| split identity | `61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6` |
| expected first-phase supply output | `eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae` |

## Read rule (fixed here)

The A/A carries no admission of its own. Its own READ (SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-PAIRED-READ-V1) reports the pair (sealed AGREE arm, wave A/A) on intent accuracy and official pooled SLU-F1 with a paired row bootstrap -- the cross-flight offset of the resident session at the wave's flight time -- beside the Fold A own-null half-widths (intent 0.9943 / SLU 1.2485; docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d), as CONTEXT for the three arm reads, never as a gate on them and never as a claim. Each wave arm's no-harm verdict is its own package's rule, read at THIS A/A.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The A/A replicate is the INSTRUMENT, not a claim: it re-flies the retained AGREE arm's own bytes so the knowledge wave's arms W1, W3 and W4 (owner decision 164) are each read against a within-chain null flown in the same chain on the same resident session (rule 3; the decision-160 precedent of one shared A/A). Its expected effect against the sealed AGREE arm (SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1, the request-identical source of its bytes, proven by shared-aa-proof-v1.json) is exactly zero by construction; a non-zero read on that pair is a measurement of the cross-flight offset, which is what it is for.",
      "primary_metric": "intent accuracy (scenario_action exact) and official pooled SLU-F1, as the instrument",
      "replicate_run_id": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
      "rows": 1080
    }
  }
}
```

## Budgets and failure rule

11,880 generation contacts (run-cumulative), 47,520 FIT endpoints, 33,930
repeated speech seconds, 12.0 GPU hours, one official complete score. Expected about 4,385 contacts at the AGREE
arm's rate. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. A failed A/A
stops the wave chain.

## Prohibitions

Never reported as a gain or as a result of its own. No paper-scale profile, no test-split, Fold B or DEV contact, no
comparator re-flight, no change against the AGREE arm's bytes, no flight before root mints the receipt and the cell is
flipped, and `--allow-output-change` is never passed.
