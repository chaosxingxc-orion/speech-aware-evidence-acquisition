# Per-scenario intent-error AUROC (all 18 gold scenarios)

Reported per the standing rule that every verdict carries its per-stratum table.

**Read it with the null replicate's warning attached.** `SAEA-SLURP-DEV1000-NULL-
REPLICATE-V1` moved intent by -5.13 to +5.41 pp across these same 18 scenarios with
NOTHING changed, so a per-stratum reading is not admissible without its own replicate.
The gold scenario is a REPORTING STRATUM only and never reached the model.

| scenario | n | intent errors | `min_token_logprob` (primary) | `intent_mean_token_logprob` | `intent_min_token_logprob` |
|---|---:|---:|---:|---:|---:|
| `alarm` | 58 | 6 | 0.6026 | 0.9872 | 0.9936 |
| `audio` | 30 | 8 | 0.9034 | 0.9489 | 0.9261 |
| `calendar` | 61 | 20 | 0.6451 | 0.8232 | 0.8305 |
| `cooking` | 37 | 15 | 0.5879 | 0.8091 | 0.7909 |
| `datetime` | 61 | 11 | 0.7727 | 0.8782 | 0.8745 |
| `email` | 61 | 9 | 0.6303 | 0.8568 | 0.8504 |
| `general` | 61 | 37 | 0.5023 | 0.5338 | 0.5315 |
| `iot` | 61 | 9 | 0.7735 | 0.9423 | 0.9423 |
| `lists` | 60 | 8 | 0.8293 | 0.9255 | 0.9423 |
| `music` | 51 | 11 | 0.8 | 0.7295 | 0.7364 |
| `news` | 60 | 13 | 0.7365 | 0.9034 | 0.8969 |
| `play` | 60 | 36 | 0.7141 | 0.8993 | 0.8727 |
| `qa` | 60 | 24 | 0.7488 | 0.8495 | 0.8472 |
| `recommendation` | 60 | 17 | 0.6689 | 0.6224 | 0.5992 |
| `social` | 60 | 10 | 0.804 | 0.938 | 0.948 |
| `takeaway` | 39 | 11 | 0.763 | 0.8182 | 0.8166 |
| `transport` | 60 | 16 | 0.5341 | 0.8509 | 0.831 |
| `weather` | 60 | 4 | 0.9866 | 0.9955 | 1.0 |

# Where the row minimum actually lands

The diagnostic the 0.69-vs-0.85 gap demands, and the direct descendant of the
2026-08-14 P1 ceiling verdict's finding 1 (*every logprob-flagged span on the clean
Earnings samples was function-word/boundary text; zero overlap with the real entity
errors*). Here the question is asked of a short structured answer, where the
candidates are JSON punctuation, the intent label, and the entity filler.

| region of the reconstructed answer | all rows | rows the official scorer marks CORRECT | rows it marks an INTENT ERROR |
|---|---:|---:|---:|
| `json_punctuation` | 491 | 420 | 71 |
| `scenario_value` | 120 | 56 | 64 |
| `action_value` | 96 | 36 | 60 |
| `filler_value` | 211 | 159 | 52 |
| `other` | 82 | 64 | 18 |

**491 of 1,000 rows put their least-confident token on JSON punctuation**, and the
split by label is the whole story: 420 of the 735 correct rows (57.1 %) do, against
71 of the 265 intent-error rows (26.8 %). The single most common minimum token is
`" []"` -- the empty entity list -- on 208 rows, followed by `"{\""` on 164 and
`" [{\""` on 75. On the error side the intent label carries the minimum on 124 of 265
rows (46.8 %) against 92 of 735 (12.5 %) on the correct side.

So the whole-answer minimum spends most of its ranking budget on the model's
hesitation about *how many entities to emit*, which is a formatting decision, and the
2026-08-14 result repeats in structured form. That is exactly what the intent-span
statistics were preregistered to separate, and they do.

