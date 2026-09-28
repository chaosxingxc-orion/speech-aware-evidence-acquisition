# CATCHALL: an offline catch-all intent rule over the sealed sample pools

Registered 2026-09-27 before any number is read (owner decision 171). **Offline only: no flight is
registered.** An arm follows only if this read clears the pool's offline floor. The exposure row is DRAFT,
root countersignature pending; nothing here authorises a contact, a receipt or an admission entry.

**Why.** `general_quirky` is the catch-all intent. On the AGREE arm it is the CATCH-ALL class, 33 rows /
3.06 pp of Fold A's remaining intent error ([`docs/results/2026-09-27-slurp-agree-arm-error-sources.md`](../../results/2026-09-27-slurp-agree-arm-error-sources.md)
section 2.4: 29 of its 45 gold rows missed, 32 of 33 cross-scenario); the knowledge-content audit's K5 finds
it has no residual definition and proposes "a Perception rule that chooses it only when no candidate's
activation holds" ([`docs/results/2026-09-27-slurp-knowledge-content-audit.md`](../../results/2026-09-27-slurp-knowledge-content-audit.md));
the boundary-key diagnostic (section 7) finds no compact key reaches it but that the `agree-1` exemplar
vote reaches the all-utterances signal at +1.4 tokens per row without a boundary rebuild; and the
synthesis lists "a catch-all intent decision that is a rule over the evidence, not an extra candidate" as a
missing capability (section 7, item 5; section 4.2 ceiling at most 3.33 pp on Fold A).

## The rule (one registered form, no tuning)

- **Signal**: the row's `agree-1` vote -- the self-excluded share of its own top-20 sealed TRAIN-exemplar
  recall whose frozen build-time `task_target` is each intent (`saea-phase-agreement-v1`, the table the AGREE
  arm consumes). Gold-free by construction.
- **Mark**: `intent-boundary:general_quirky` holds the STRICT maximum share (a tie never marks).
- **Decision**: on a marked row, every well-formed sample whose intent is not `general_quirky` is delivered
  as scenario `general`, action `quirky`, its entities byte-unchanged. Unmarked rows and malformed samples
  are never edited.

## Which pools carry the signal

| pool | roster | agreement table (sha256) | stage 1-3 per-sample read | rows marked | role |
| --- | --- | --- | --- | ---: | --- |
| ROLL-1 `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` | R01C 625 | **none** (no agreement table was ever built for R01C) | present | -- | not readable without a new preparation |
| ROLL-2 `SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1` | TRAIN Fold A 1,080 | `SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1` (`018ca6ef...`) | **absent**: `scripts/flights/batch/roll2_read.sh` (5 scorer jobs) has not run | 20 (from the table alone) | **primary** |
| ROLL-3 `SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1` | DEV-2000-ADDED 1,000 | `SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1` (`283bd9f5...`) | present (`SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-READ-V1`) | 19; 66 of 95 samples edited, 29 already catch-all | fresh-roster replication |

(`--dry-run` counts, no score read.) The vote is not recorded inside any sealed pool flight -- ROLL-2 and
ROLL-3 flew the locked plan at `w_agree` 0 -- it is the pinned model-free table of the same roster, joined
by sample id.

## The read and the floor

`scripts/analysis/catchall_offline_read.py --pool {fold-a,dev2000-added}`: the rule edits each of the five
rendered sample copies of the pool's stage 1-3 read, each edited copy is scored ONCE through the same
registered scorer (`score_copy`; gold enters only inside the official scorer, as in every offline read of
this programme), and `RULE-mean-single` is contrasted with `R0-mean-single` under the aggregation read's own
paired row bootstrap (`slurp_sample_aggregation_offline_read.bootstrap`, imported unchanged; 10,000 draws,
seed 20260915) -- the resampling that measured the 0.67 pp floor.

**Floor.** The instrument note's offline-sealed-pool floor, 0.67 pp at n = 625 (section 2d), scaled as
`stage3_effect_floor_check.py` scales it: **0.5097 pp at Fold A's 1,080 rows** (primary) and 0.5299 pp at
DEV-2000-ADDED's 1,000.

**Decision (fixed now).** The rule CLEARS a pool when the intent delta's CI95 lower bound is above zero,
the point delta is at least that pool's floor, and the official SLU-F1 guard's CI95 lower bound is at least
minus the floor. An arm (with an in-chain A/A) is registered only if **Fold A clears**; DEV is read beside
it. **Reach ceiling** (not a forecast): 20 marked Fold A rows x 0.0926 = 1.85 pp if every marked row were a
gold catch-all and every sample converted; 13.2 row-equivalents of edits on DEV = 1.32 pp.

**`stage3_measurement`**: `offline-sealed-pool`, 1,080 rows, `expected_effect_pp` 0.51 (the smallest effect
this read is registered to see, equal to its floor -- not a forecast). **`stage3_algorithm`**: `none`,
operators `[]` -- one fixed commit rule read once over a sealed pool, with no rollout, no credit assignment,
no update and no search. It is deliberately NOT labelled `sealed-credit-system-policy-v1`, whose first
instance every single-factor cell of this programme leaves to the composed system policy.

**Not authorised.** No flight, no contact, no scoring before the ledger row is countersigned, no Fold B /
test read, no tuning of the mark (a different threshold is a new registration).

| file | holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-catchall-offline-v1-preregistration.md` | the preregistration and its fence |
| `registered-facts-v1.json` | pools, hashes, dry-run counts, floor, decision, the CANONICAL `stage3_measurement` |
