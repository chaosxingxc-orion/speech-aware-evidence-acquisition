# The replication guard table -- REPLICATED

Call-clustered CI90, natural mixture, 44 call clusters, 1,593 paired 90-second windows, seed 20260903, 10000 replicates. Percentage points. Signed replicate minus comparator; the margin is applied one-sidedly, on the harmful side only.

| guard | required | replicate | first pass (v2) | verdict |
|---|---|---:|---:|---|
| delivery integrity (construction) | construction; aborts the read | 1593 / 1,593 windows, 0 violations | 1593 / 1,593, 0 violations | PASS |
| corpus WER non-inferiority | upper bound <= +0.05793 | -0.03090 (point -0.04642) | -0.02936 | PASS |
| numeric-value accuracy not worse (call-pooled) | lower bound >= -0.15651 | -0.07745 (point -0.03082) | -0.02122 | PASS |
| over-generation not worse | upper bound <= +0.02218 | +0.00328 (point +0.00139) | +0.00255 | PASS |
| negation-critical / semantic high-impact rate | advisory; gates nothing | +0.00000 | -0.00028 | ADVISORY |

| primary leg | required | measured | disjoint from the PERSON null? | verdict |
|---|---|---|---|---|
| vs_comparator | LB > +0.25680 | +3.634 [+2.590, +4.690] | YES | MET |
| vs_ku_e1fc | LB > +0.00000 | +3.737 [+2.686, +4.773] | YES | MET |

## The replication contrast -- first pass versus replicate, against the carrier's own null band

| metric | replicate - first pass | CI90 | null band | inside? |
|---|---:|---|---|---|
| entity_wer_PERSON | +0.10285 | [-0.33075, +0.56023] | [-0.24338, +0.25680] | YES |
| corpus_wer | -0.00139 | [-0.00842, +0.00502] | [-0.08502, +0.03085] | YES |
| entity_wer_ORG | -0.29796 | [-0.61713, -0.02448] | [-0.44313, +0.26904] | YES |
| non_entity_wer | +0.00066 | [-0.00329, +0.00474] | [-0.11375, +0.01575] | YES |
| numeric_accuracy_call_pooled | -0.04109 | [-0.07574, -0.01042] | [-0.18758, +0.12543] | YES |
| insertions_per_reference_word | +0.00111 | [-0.00056, +0.00279] | [-0.01356, +0.03079] | YES |
| negation_critical_rate | +0.00028 | [+0.00000, +0.00080] | [+0.00080, +0.00377] | NO |
