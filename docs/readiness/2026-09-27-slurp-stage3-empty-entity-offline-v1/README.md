# EMPTYENT: the DEV-2000-ADDED pool's offline null, then an explicit empty-entity rule read against it

Registered 2026-09-27 before any number is read (owner decision 171). **Offline only: no flight is
registered.** The exposure row is DRAFT, root countersignature pending; nothing here authorises a contact,
a receipt or an admission entry.

**Why.** The synthesis ranks "an explicit empty-entity decision fed by sample agreement on emptiness" fourth
([`docs/results/2026-09-27-slurp-mechanism-synthesis.md`](../../results/2026-09-27-slurp-mechanism-synthesis.md)
section 5): 114 of 191 empty-gold R01C rows emit entities, the ENTITY-FP-ONLY class is **12.1 % / 10.8 %** of
Fold A / DEV rows, the support filter's +1.40 was FP suppression, and F10 made emptiness explicit only on a
pooled number. It prescribes an OFFLINE read over the sealed pools first, a flight only if it clears. DEV's
sealed ROLL-3 pool has within-pool half-widths (instrument note section 2e) but **no offline floor of the
section 2c kind**, so this registration measures that null first.

## Step 1 -- the offline null (no scorer contact)

`scripts/analysis/empty_entity_offline_read.py --pool dev2000-added --stage null`. The quantity: the paired
CI95 half-width between two samples' entity answers under `slurp-slu-official-projected-v3` (the pooled
official SLU-F1, micro over word- and char-distance TP/FP/FN -- the entity-only metric), for all ten
sample-index pairs, plus each sample against `R0-mean-single`.

**The resampling, copied exactly from the instrument note's one-pool offline floor** (section 2c: the
aggregation read's medoid rule, CI95 [-0.63, +0.71] at n = 625, hence 0.67 pp; section 2d's
offline-sealed-pool row): the aggregation read's own `bootstrap`
(`scripts/analysis/slurp_sample_aggregation_offline_read.py`), imported byte-unchanged, not re-implemented --
a PAIRED ROW bootstrap: `rng = numpy.random.default_rng(20260915)`, `indices = rng.integers(0, n, size=(10000, n))`,
per-draw row weights by `bincount`, every arm's pooled official counts re-summed on the SAME draws, and the
2.5 / 97.5 percentiles of (arm - baseline) as the CI95. The resampling unit is the ROW, as in section 2c.
Section 2e's DEV widths (1.19 per-row, 1.56 pooled micro) used a different unit (whole-utterance clusters,
`analysis.paired.resampled_statistic`); `--with-cluster-variant` reports that variant beside the null for
comparison, never as the null.

**THE NULL** = the mean over the ten pairs of the pooled SLU-F1 half-width (max reported beside it); the
intent guard = the mean pairwise intent half-width. Both are sealed in `null.json` before step 2 runs, and
step 2 reads them from that file.

## Step 2 -- the empty-entity rule (five scorer contacts, on copies)

- **Emptiness vote**: per row, the number of well-formed samples (of 5) whose answer carries no entity.
- **Rule** (one registered form): vote >= 3 (a majority of five) -> every sample of the row is delivered with
  an empty entity list, scenario and action unchanged. Malformed samples never vote and are never edited.
- Each edited copy is scored ONCE through the registered scorer (gold enters only inside the official
  scorer); `RULE-mean-single` vs `R0-mean-single` under the same bootstrap.
- **CLEARS** iff the SLU-F1 CI95 lower bound > 0 AND the SLU-F1 delta >= THE NULL AND the intent CI95 lower
  bound >= -(the intent guard). A clear licenses registering an arm with an in-chain A/A; nothing else.

**Dry-run counts (no score read)** on DEV-2000-ADDED: 1,000 rows x 5 samples; 17 malformed samples; 1,039
empty samples; 118 rows empty on all five; the rule fires on **203 rows** and edits **123 samples** (24.6
row-equivalents per mean single sample). TRAIN Fold A (ROLL-2) is read beside it once its registered stage
1-3 read (`scripts/flights/batch/roll2_read.sh`) exists.

**`stage3_measurement`**: `offline-sealed-pool`, 1,000 rows, `expected_effect_pp` 0.53 (the gate's
offline floor at n = 1,000, the smallest effect registered to be seen -- not a forecast; the registered
decision bar is THE NULL, which may be larger). **`stage3_algorithm`**: `none`, operators `[]`.

**Not authorised.** No flight, no contact, no scoring before the ledger row is countersigned, no Fold B /
test read; a `--min-empty` other than 3 is descriptive and carries no decision.

| file | holds |
| --- | --- |
| `../2026-09-27-slurp-stage3-empty-entity-offline-v1-preregistration.md` | the preregistration and its fence |
| `registered-facts-v1.json` | pool, hashes, the copied resampling, dry-run counts, decision, the CANONICAL `stage3_measurement` |
