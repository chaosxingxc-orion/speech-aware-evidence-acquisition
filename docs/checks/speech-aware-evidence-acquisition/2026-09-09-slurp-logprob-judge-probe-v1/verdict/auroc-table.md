# AUROC of every preregistered confidence statistic

Speaker-cluster bootstrap, 10,000 replicates, seed 20260908, CI90, mid-rank ties.
`n = 1,000` rows in `124` speaker clusters. Every statistic is oriented so a LOWER
value means LESS confident, so the flag score is the negated statistic throughout.

**The rule turns on `min_token_logprob` against `intent_error`, and only on that cell.**
It was fixed as the primary before the flight; every other row here is a preregistered
measurement, not an alternative verdict.

| statistic | intent error AUROC | CI90 | any-slot error AUROC | CI90 |
|---|---:|---|---:|---|
| `min_token_logprob` **(PRIMARY)** | 0.6935 | [0.6660, 0.7202] | 0.6534 | [0.6262, 0.6804] |
| `mean_token_logprob` | 0.7364 | [0.7104, 0.7629] | 0.6391 | [0.6118, 0.6659] |
| `intent_mean_token_logprob` | 0.8497 | [0.8262, 0.8729] | 0.4795 | [0.4497, 0.5097] |
| `intent_min_token_logprob` | 0.8446 | [0.8211, 0.8683] | 0.4739 | [0.4442, 0.5041] |
| `first_intent_token_margin` | 0.7869 | [0.7592, 0.8131] | 0.4768 | [0.4462, 0.5089] |

Two readings the table makes unavoidable.

1. **The whole-answer minimum is the weakest intent predictor of the five** (0.6935) and
   the strongest slot predictor (0.6534). The intent-span statistics are the exact
   mirror: 0.8497 on intent and 0.4795 -- chance -- on slots. A confidence statistic
   predicts the thing its tokens are part of, and nothing else.
2. **The two intent-span statistics clear the rule's arm-A bar** (>= 0.75 point,
   CI90 lower bound >= 0.70) with room to spare. They are not the primary, so they do
   not admit anything here; what they do is price a successor preregistration.

