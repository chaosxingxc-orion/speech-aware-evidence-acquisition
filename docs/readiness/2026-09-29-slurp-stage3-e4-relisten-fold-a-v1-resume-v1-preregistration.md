# Cell E4-1 recovery: SEAL-ONLY completion of the aborted arm (HELD)

Status: **REGISTERED BEFORE CONTACT, HELD until owner decision 194** (the same shape as owner decision 189
option A for COMP-1). Written with zero model, tokenizer, encoder, scorer, server and GPU contacts. No utterance
text, transcript, gold label, shadow-column value or model output is printed or persisted anywhere in this package:
ids, counts and hashes only.

This note addends the E4-1 registration
[`2026-09-29-slurp-stage3-e4-relisten-fold-a-v1/`](2026-09-29-slurp-stage3-e4-relisten-fold-a-v1/) and its
preregistration, which are **not edited**. Everything they fix stands unchanged and is not re-litigated: the question,
the one factor (the post-accept relisten block), the two shadow columns, the decision rule, the bar (the design's own
null), the claim ceiling `nominated` and the prohibitions.

## 1. What aborted

The arm attempt `attempt-slurp-native-stage3-relisten-fold-a-generation-v1` of run
`SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1` (flight commit `e9777e18`) flew all 1,080 rows (6,304 contacts, 18,730.5 s of
repeated speech). It then ABORTED at the seal with `FlightRuntimeError: finite source is not the last actual sample
contact`. The trace SHA-256 is `966613e416dd81c9cd5bbdc21b16050f394844e5b9da6522ed8451b1f1f233f6`.

Root cause, named to a component: on 8 of the 10 finite-completion rows, the post-accept relisten stage spent its
shadow contacts after the interrupted source contact, and the seal's finite-source rule compared the source with the
last recorded contact. The fix is `b286d8974` (`fable/e4sealfix`, merged). The README of this package gives the full
account and the scratch rehearsal.

## 2. The seal-only cell

| item | value |
| --- | --- |
| experiment / cell | `slurp-native-stage3-relisten-fold-a-v1-resume` |
| run id | `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1` (unchanged) |
| generation attempt | `attempt-slurp-native-stage3-relisten-fold-a-generation-v1-seal-only` |
| FIT run / attempt | `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-FIT-V1` / `attempt-slurp-native-stage3-relisten-fold-a-fit-v1-seal-only` (fresh, records no contact) |
| `resume_from` | the aborted attempt, trace `966613e4...` |
| rows | 1,080 kept under I7r custody without selection; 0 flown |
| budget | run-cumulative 6,304 of 18,360; the completion adds 0 |
| replay proof | 1,080 checked, 0 failing, 0 sealed twice (read-only, on the real trace, at master `109538e8`) |

## 3. Reading

The E4-1 column read is unchanged. It runs by the READ row `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1` over the
seal-only attempt's sealed manifest, and the manifest's predecessor block must name trace `966613e4...`. The relisten
receipts are the ones the fixed resume replay re-derives from the trace. Development numbers only (owner decisions 28
and 86); never a test claim.
