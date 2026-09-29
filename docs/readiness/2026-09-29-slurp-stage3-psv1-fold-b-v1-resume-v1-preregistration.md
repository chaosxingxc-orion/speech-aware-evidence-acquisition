# Cell P-SV-1 recovery: SEAL-ONLY completion of the aborted arm

Status: **REGISTERED BEFORE CONTACT under owner decision 197** (the same shape as owner decision 194 for E4-1 and
owner decision 189 option A for COMP-1). Written with zero model, tokenizer, encoder, scorer, server and GPU contacts.
No utterance text, transcript, gold label, branch-column value or model output is printed or persisted anywhere in this
package: ids, counts and hashes only.

This note addends the P-SV-1 registration
[`2026-09-29-slurp-stage3-psv1-fold-b-v1/`](2026-09-29-slurp-stage3-psv1-fold-b-v1/) and its preregistration, which
are **not edited**. Everything they fix stands unchanged and is not re-litigated: the question, the three Perception
branches (b-top2contrast, t-twin, a-agree delivering) at level 2, the read, the bar (the in-flight twin null), the claim
ceiling `nominated` and the prohibitions.

## 1. What aborted

The arm attempt `attempt-slurp-native-stage3-psv1-fold-b-generation-v1` of run `SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1`
(flight commit `b9af3e58`) flew all 1,080 rows (8,709 contacts, 25,428.7 s of repeated speech). It then ABORTED at the
seal at 14:19:36Z on the seal invariant I7v (perception-branch receipt: `candidate_intent_ids` must be a non-empty
ordered list of distinct non-empty strings). The trace SHA-256 is
`0c1edb20c37756ec8567fbba8edc56d8ff24ce3ea32b94bccad8c3667285d20a`.

Root cause, named to a component: the runner sealed each branch note's intent list verbatim, and 61 notes over 49 rows
listed one intent twice (a-agree 21, b-top2contrast 17, t-twin 23). The fix is `6fb31f8d3` (`fable/psvsealfix`, merged
at `0177f83fc`). The README of this package gives the full account and the scratch rehearsal.

## 2. The seal-only cell

| item | value |
| --- | --- |
| experiment / cell | `slurp-native-stage3-psv1-fold-b-v1-resume` |
| run id | `SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1` (unchanged) |
| generation attempt | `attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only` |
| FIT run / attempt | `SAEA-SLURP-STAGE3-PSV1-FOLD-B-FIT-V1` / `attempt-slurp-native-stage3-psv1-fold-b-fit-v1-seal-only` (fresh, records no contact) |
| `resume_from` | the aborted attempt, trace `0c1edb20...` |
| rows | 1,080 kept under I7r custody without selection; 0 flown |
| budget | run-cumulative 8,709 of 16,200; the completion adds 0 |
| replay proof | 1,080 checked, 0 failing, 0 sealed twice (read-only, on the real trace, at master `0177f83fc`) |
| measurement | the parent's `stage3_measurement` with `primary_metric_key: "intent"` (decision 190) |

## 3. Reading

The P-SV-1 branch read is unchanged. It runs by the READ row `SAEA-SLURP-STAGE3-PSV1-FOLD-B-BRANCH-READ-V1` over the
seal-only attempt's sealed manifest, and the manifest's predecessor block must name trace `0c1edb20...`. The
perception-branch receipts are the schema-v2 ones the fixed resume replay re-derives from the trace; a note whose
`note_parse_status` is `empty` or `malformed` counts as gold-absent. Development numbers only (owner decisions 28 and
86); never a test claim.
