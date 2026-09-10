# Draft decision: retain KC-E1f; do not admit E21 LOOP as the replacement

**Status: owner review draft.** This document records frozen completed evidence.
The machine decision remains owner-owned.

## Decision

The LOOP judge has a positive paired result against its randomized twin, but it
does not retain the historical KC-E1f quality floor. It is therefore **not
admitted as the E21 replacement**. Retain KC-E1f as the preferred E21 quality
component. Do not schedule a new LOOP GPU experiment from this result.

The primary natural-mixture PERSON comparison against KC-E1f is+ßuÁ‚ùÁR1.714090
percentage points, CI90 ZÈ›y¯ßy“2.564917, ∫w^~)ﬁv0.886179]. Its lower bound is below the
inherited retention floor of"È›y¯ßy“0.25009 percentage points. That single failed
frozen gate is decisive.

## Frozen evidence and scope

The compact frozen contrast table is
`DATA/analysis/SAEA-E21-LOOP-PACKETS-NP4-SAVED-SCORE-ANALYSIS-V1/loop-contrast-compact-tables.json`,
SHA-256 `4e2200d863a828f665701341f9bc0ecbafbb76bbf67b7ffebab01bb489484a70`.
It records no new model, encoder, reference, or scorer contacts.

| completed artifact | SHA-256 |
|---|---|
| Judge generation manifest | `a74e1d3191b9b069c44b0eec81e0550b9c1f6fc990eb073b8b06f21e2df37d09` |
| Twin generation manifest | `df2905190a86de0f97616e46a1bf6a30fb3881dc845048884fc3fc59fd99defb` |
| Judge complete-score receipt | `c3d32e37e46a91d9cab589e3db05274df89ab04faaba4248fd5278478f997bb9` |
| Twin complete-score receipt | `d4da75685fc8161a1e0948156b10da86cbbbd2b65f90e809a841aaeab4371290` |
| Judge full score | `6282411f60e6f7ecba36a61cb9dea9f677698be028e16c8b0396515264512e2c` |
| Twin full score | `0e62b00a45dae7ef9177a99aa6f0914a9dbef49c966d51366860238f251ab34b` |

Each arm sealed 600 selected contacts, zero retries, zero skipped slices, and
zero saturated slices. Each retained 993 unselected predecessor windows, so
the derived output roster remains 1,593 windows across 44 calls. Pair external
GPU utilization was 0.3579660937786103 hours.

The judge had an archived seal incident: initial sealing refused a stale root
lease after all 600 contacts completed. The recovered sealed manifest binds
the archived custody record
`e21-loop-judge-seal-failure-custody-v1.json` SHA-256
`b0fa57ef727229f25a748f065e69049cd32cafeebebc41342dc67ba6f4b55ec4`.
It is not a retry or an additional generation attempt.

Historical KC-E1f used raw-audio windows. The completed LOOP arms use current
formal speech-feature packets. This protocol difference remains explicit; the
historical comparison is a frozen quality comparator, not wire-level parity.

## Frozen gates

| Gate | Natural mixture | Equal-call sensitivity | Result |
|---|---:|---:|---|
| Judge"È›y¯ßy“ twin PERSON | +1.474117 [ +0.849923, +2.136136 ] | +1.755367 [ +1.001335, +2.525865 ] | Pass |
| Judge"È›y¯ßy“ historical direct PERSON | +2.022626 [ +1.368053, +2.728592 ] | +2.432400 [ +1.556625, +3.351493 ] | Pass |
| Judge+ßuÁ‚ùÁR KC-E1f PERSON; retention LB+ßuÁ‚ùÁe"È›y¯ßy“0.25009 | ∫w^~)ﬁv1.714090 [ ∫w^~)ﬁv2.564917,+ßuÁ‚ùÁR0.886179 ] |"È›y¯ßy“1.267347 ["È›y¯ßy“2.133838, ∫w^~)ﬁv0.388111 ] | **Fail** |
| Realized core calls+ßuÁ‚ùÁd 796.5 | 600 | 600 | Pass |
| Judge ∫w^~)ﬁv direct WER | +0.018901 [ +0.012440, +0.025899 ] | +0.022953 [ +0.014954, +0.031438 ] | Pass |
| Judge+ßuÁ‚ùÁR direct numeric | +0.000000 [ +0.000000, +0.000000 ] | +0.000000 [ +0.000000, +0.000000 ] | Pass |
| Judge+ßuÁ‚ùÁR direct insertion; UB"È›y¯ßy‘ +0.02218 | +0.000278 [ +0.000000, +0.000817 ] | +0.000238 [ +0.000000, +0.000714 ] | Pass |

All values are percentage points in the preregistered favorable direction.
Equal-call is a sensitivity view; the natural mixture supplies the decision
gate. WER, numeric, and insertion results do not repair the failed KC-E1f
retention gate.

## Complete descriptive PERSON table

The table below reports the frozen call strata. It is descriptive only:
no stratum is an additional gate. Gains are judge minus the named comparator,
in percentage points.

| Sector | n | Judge ∫w^~)ﬁv twin | Judge ∫w^~)ﬁv KC-E1f |
|---|---:|---:|---:|
| Basic Materials | 5 | +1.372998 |+ßuÁ‚ùÁR0.686499 |
| Conglomerate | 4 |+ßuÁ‚ùÁR0.785340 |+ßuÁ‚ùÁR3.141361 |
| Consumer Goods | 5 | +1.400560 |"È›y¯ßy“2.240896 |
| Financial | 5 | +1.423488 |"È›y¯ßy“1.779359 |
| Healthcare | 5 | +0.638978 |+ßuÁ‚ùÁR3.514377 |
| Industrial Goods | 5 | +2.295918 | ∫w^~)ﬁv0.255102 |
| Services | 5 | +2.970297 |+ßuÁ‚ùÁR2.475248 |
| Technology | 5 | +3.488372 | +2.325581 |
| Utilities | 5 | +2.099738 | ∫w^~)ﬁv2.362205 |

| Sample rate (Hz) | n | Judge+ßuÁ‚ùÁR twin | Judge+ßuÁ‚ùÁR KC-E1f |
|---|---:|---:|---:|
| 11,025 | 5 | +0.294985 |"È›y¯ßy“0.294985 |
| 16,000 | 6 | +4.804805 |"È›y¯ßy“0.900901 |
| 22,050 | 5 | +2.631579 | +0.751880 |
| 24,000 | 21 | +1.152959 |+ßuÁ‚ùÁR3.228286 |
| 44,100 | 7 | +0.589970 |+ßuÁ‚ùÁR0.884956 |

## Existing-config route for the retained live quality system

The smallest existing route is the historical two-stage KC-E1f composition:
`configs/experiment/e21-full44-direct-baseline-v1.json` supplies the actual
full44 initial draft, then
`configs/experiment/e21-kc-e1f-repair-44-v1.json` with baseline
`configs/baseline/e21-kc-e1f-brief-repair.json` applies the registered
`e21-entity-repair-substitutions-v1` constrained repair and its existing
predecessor binding.

The repair experiment currently points to a sealed predecessor, so a live
current-executor successor must replace that predecessor pin with the newly
sealed direct manifest and register the two stages, their request fits,
capacity, and exposure rows. This is a configuration and lifecycle binding of
the existing initial-draft-plus-repair mechanism. It does not require a new
E21 policy, reviewer, retrieval method, or LOOP extension. The historical
raw-audio versus current formal-packet choice must remain explicit in that
successor, and owner admission is still required before any contact.
