# Eval Definition: A2T Executable Ground Qualification 104 V1 Roster

## Capability evals

| id | criterion |
|---|---|
| E01 | The three pinned source receipts match their SHA-256 and split identities. |
| E02 | Selection produces exactly 13 items in each canonical tier and 104 items total. |
| E03 | Selected sample identities and tier-scoped query blocks are unique and have zero overlap with both excluded cohorts. |
| E04 | Selection is parent-order independent and uses only the frozen hash namespace plus runtime-legal identity/media fields. |
| E05 | Every selected media file exists and its local duration, WAV header, and SHA-256 are receipted. |

## Regression evals

| id | criterion |
|---|---|
| R01 | Existing G1 and CPV2 cohort tests remain green. |
| R02 | The selector type cannot accept query text, expected calls, gold, model outputs, scores, rewards, or test annotations. |
| R03 | The proposed unexposed 400-item tier is not opened, registered, or changed. |
| R04 | Offline execution records zero model, tokenizer, retriever, embedding, network, audio-decode, scorer, GPU, gold, and test contact. |

## Success rule

All capability and regression evals pass on the first registered materialization. Failure closes the
roster run and permits only a separately preregistered model-free successor; no selection namespace,
tier allocation, or exclusion rule may change after identities are seen.
