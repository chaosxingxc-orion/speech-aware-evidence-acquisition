# Cell RANKVIS read: m = 19 of 119 wrong-to-gold conversions against a no-op expectation of 15.9 rows (DESCRIPTIVE)

Read 2026-09-28T23:39Z (UTC; note dated for the reporting day) by Claude Opus 5.5 in the worktree
`fable/rankvisread`. The registered model-free read row `SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-119-V1-READ-V1`
(recipe `slurp-stage3-rankvis-fold-a-119-conditional-rate-v1`) was ROOT COUNTERSIGNED 2026-09-28 23:37 UTC by
the coordinator (Fable 5.1) after the seal and before the read (owner decisions 171 and 178). It ran through
`scripts/flights/rankvis/rankvis_read.sh` -> `scripts/analysis/rankvis_probe_read.py` (sha256 at run
`d96123dab9c9303409552658b7398753e2bc6452f3979fbc0cb886fea0560aeb`, after the two locator repairs of section 7).
Outputs under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-119-V1-READ-V1/`: `read-v1.json`
(sha256 `d584b58e776b327119e68c7b5b8fee6fe0776716045e7615a8969e474245d1ac`), `read-v1.md` (sha256
`e774eeb3f47d9f266dfec5dae91b2c6ae08a8cee20bc160e4bb55f744cee9183`); the two earlier refusal receipts were
overwritten in place by the same path (`refusal-v1.json`, see section 7). Model-free throughout: zero model,
tokenizer, encoder, embedder, scorer, server and network contacts. No utterance text, gold label string,
transcript, knowledge content or model output is printed or persisted here; ids, counts, rates and hashes only.

**DESCRIPTIVE.** The number and the side of the pre-declared rule it falls on; the verdict word is the
coordinator's (decision 139). A CONDITIONAL rate on a gold-selected TRAIN Fold A roster: never a pooled
effect, never a roster-level claim, never a test claim (decisions 28, 86). The probe is a form proof under
200 rows and claims no benefit.

## 1. What flew

Driver step 1 (`rankvis`) of the one-step chain `SAEA-Queue-RANKVIS-SUB10` at flight commit `b0c6c608`
(arm-start 23:18:05Z, arm-exit rc 0 23:36:11Z, driver-done 23:36:32Z). The comparator is the sealed AGREE arm
`SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (attempt `attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1`),
not re-flown; the contrast is per row and offline.

| run | rows | model contacts | speech s | prompt tokens | completion tokens | state |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-119-V1` | 119 (119 distinct) | 486 | 1,287.725 | 4,375,903 | 30,668 | COMPLETED, FINALIZED, scored once |

One episode per row (486 model contacts over the phase program, about 4.1 per row); zero tool calls, zero
requests carrying tool schemas; two rows took the `finite_completion` disposition; study tree clean at seal;
wall time about 18 minutes. Sealed hashes: run manifest `2dfe32d05febd2bbcfb17cb70dbc64093f26d79d565f89481777a977bc0543f3`,
outputs `2a5e2f1917e82120549ebad1820ce2ce64baf03c227b68ece708b2a236900afd`, scores
`c0b3d19b3f96c09d31d89fd8bef94a736f54ed38361555fa49f6b55e43547bc9`.

## 2. Rendering gate: PASSED

Verified directly from the sealed MODEL_REQUEST records the flight wrote (`rails.runner.RANK_VISIBLE_LABEL`):
every value line of each named store's block carries the rank label, the ranks read 1..n contiguous and
strictly increasing in document order, and the count equals the store's delivered count in the sealed phase
receipt.

| store | rows verified / total | failed |
| --- | ---: | ---: |
| intent-boundaries | 119 / 119 | 0 |
| train-exemplars | 119 / 119 | 0 |

Informational only: the probe's first-phase seed order equals the comparator's on 119 / 119 rows; the optional
retrieval-rank-inputs sidecar cross-check was not available (no sidecar sealed; 119 rows unverifiable by that
stricter route, which the registered gate does not require).

## 3. The number

| quantity | value |
| --- | ---: |
| m, rows moved wrong to gold (of 119) | **19** (15.97 %) |
| Wilson CI95 | [10.47 %, 23.59 %] (12.5 to 28.1 rows) |
| Clopper-Pearson CI95 | [9.90 %, 23.81 %] |
| no-op expectation (never zero) | 15.906 rows (13.37 %) |
| m - no-op | +3.09 rows |
| pre-declared 89-row synthesis sub-read | m = 9 of 89 (10.11 %), Wilson [5.41 %, 18.11 %], Clopper-Pearson [4.73 %, 18.33 %]; no-op 11.459; m - no-op -2.46 |

The no-op expectation (15.906 rows, 13.37 %) lies inside the full-roster interval; on the 89-row subset m sits
below its no-op expectation, also inside the interval.

## 4. Re-declaration arithmetic (stated, not applied)

- The registered rule: a later 1,080-row arm with an in-chain A/A declares
  `expected_effect_pp = (m - no-op) x 0.092593 pp` intent accuracy. Here `(19 - 15.906) x 0.092593 = 0.287 pp`.
- The 2.5 pp cross-flight bar needs m >= 43 net of the no-op (m >= 59 rows gross); m = 19 does not clear it.
- If the arm were instead read as a Solver-column variant under the same-flight floor of about 0.32 pp at
  n = 1,080, the net conversions would need to reach 0.32 / 0.092593 = 3.46 rows, i.e. m >= 20 gross;
  m = 19 (0.287 pp) sits one row under that floor as well.

## 5. Splits the driver reports

Four-way transition split (per row, probe vs sealed AGREE):

| transition | rows |
| --- | ---: |
| wrong to gold (m) | 19 |
| gold to wrong (zero by construction: AGREE holds no correct row on this roster) | 0 |
| the same wrong intent | 87 |
| a different wrong intent | 13 |

By stage (the roster derivation's stage label):

| stage | rows | m | rate (Wilson CI95) |
| --- | ---: | ---: | --- |
| CONSUMPTION-SOLVER-CHOICE | 69 | 17 | 24.64 % [15.99, 35.96] |
| CONSUMPTION-PERCEPTION-DROP | 49 | 2 | 4.08 % [1.13, 13.71] |
| UNPARSED | 1 | 0 | -- |

By the roster's AGREE gold-position band (the position of the gold intent's entry in the AGREE-delivered
boundary block; cross-tabulated here from `read-v1.json` per-row transitions and the committed roster's
`agree_gold_position_band`, not a driver table), with the band's committed null save rate:

| band | rows | m | rate (Wilson CI95) | null save rate | no-op rows |
| --- | ---: | ---: | --- | ---: | ---: |
| 1 | 18 | 14 | 77.78 % [54.79, 91.00] | 38.71 % | 6.97 |
| 2-8 | 101 | 5 | 4.95 % [2.13, 11.07] | 8.85 % | 8.94 |

## 6. Relation to the node-gain ledger

The node information-gain ledger (`2026-09-28-slurp-node-information-gain-ledger.md`) found that the Solver
follows Perception's rank 1 on 97.6 % of rows and converts a gold intent sitting at Perception rank 2 on
27 % and at rank 3 on 12 %, so intent is decided at Perception's shortlist. The RANKVIS conversions
concentrate where that picture predicts little headroom for a rendering change and much for re-flight noise:
14 of the 19 sit on the 18 rows whose gold entry already stood FIRST in the AGREE boundary block (78 % against
a committed null save rate of 39 %, 7.0 expected rows), and 17 of 19 on rows labelled
CONSUMPTION-SOLVER-CHOICE; on the 101 rows whose gold stood at boundary positions 2-8 the probe converts 5
(4.95 %), below that band's null save rate (8.85 %, 8.9 expected rows). The driver does not report the gold
intent's rank inside Perception's own emitted list for the converted rows, so the mapping from boundary-block
position to Perception rank is not established by this read; the band table above is the closest split the
sealed inputs give without a further read.

## 7. Driver repairs made before the number was read

The first two invocations refused before any score was opened (no conversion number written; refusal
receipts only), on two locator defects in the driver, both repaired in this branch and covered by the
existing `tests/unit/test_rankvis_probe_read.py` + `test_rankvis_config.py` (34 passed):

1. `READ REFUSED at step 0: the generation plan carries no 'attempt_id'`. The registered generation plan nests
   the attempt identity under `execution_plan.attempt_id`; `load_generation_plan` now reads it there (a
   top-level value is accepted only if it agrees). The sealed manifest and attempt-record checks still bind it.
2. `READ REFUSED at step 1: the committed baseline fragment does not hash to the registered facts' pin`. The
   flip (`repin_cell.py --set-ready`, commit `b0c6c608`) added exactly one key, `prepared_phase_supply`, to the
   baseline fragment after the facts were registered. `load_baseline_rendering` now accepts the fragment only
   if dropping that one key re-serialises (indent 2, trailing newline) to the registered sha256
   `524b92a9...`; it does, and the flown bytes remain bound by the manifest's config hash against the plan.

Neither repair touches the rendering gate, the estimand, the roster, the no-op expectation or the rule.

## Coordinator verdict (Fable 5.1, 2026-09-29)

**INERT (form proof; the B1 arm is not registered).** m = 19 of 119 (Wilson CI95 [10.47, 23.59] %)
against the no-op expectation of 15.9 rows: +0.29 pp net intent at n = 1,080, while the cross-flight bar
needs m >= 43 net of the no-op and a same-flight read m >= 20 gross; the probe clears neither as a basis
for an arm. The informative result is the split: rows whose gold sits at boundary position 1 converted
14 of 18 (no-op 6.97 rows), positions 2-8 only 5 of 101 -- rank labels make the Solver follow the
presented rank 1, which is consistent with the node information-gain ledger (the Solver follows
Perception's rank 1 on 97.6 % of rows). The contrast route therefore continues at Perception (P-SV-1 /
P-SV-2, owner decisions 184 and 188), not at the Solver's rendering. The driver's two path repairs
(section 7: `execution_plan.attempt_id`; the flip-added `prepared_phase_supply` key) are accepted by the
coordinator: they touch no gate, estimand, roster, no-op expectation or rule. The agent's numbers above
are unchanged.
