# The E21-LOOP-1 judge inventory, priced model-free — `SAEA-E21-MF-LOOP-1-PREP-V1`

**When a judge fires, is the row actually wrong; and of the rows that are wrong, how many does it
catch.** A judge under the Reviewer seat changes no byte of what a flight sends (WAVE W1 §2), so its
own admission question is not "does it help the score" but those two — and both are answerable at
**zero contacts**, on outputs this repository sealed on 2026-09-04.

The number this receipt exists to produce is not a precision. It is a **budget**: the count of
windows the inventory flags on the sealed draft IS the number of core calls E21-LOOP-1 spends.

| | |
|---|---|
| exposure row | `SAEA-E21-MF-LOOP-1-PREP-V1` (`model-free-check`) |
| draft | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338`, its 1,593 per-window pass-1 hypotheses recovered — never re-derived — through `analysis.e21_window_pairing` |
| truth | the ConEC alignment that same instrument charges to each window |
| brief | the ConEC participant roster's PERSON and ORG classes at the flown cap of 12, read through `core.evidence`'s own registered reader |
| carrier / split | `earnings21-original`, `discovery`, all 44 calls, split identity `fcc1b0bc…d69e` |
| contacts | **zero** — no model, GPU, server, tokenizer, tool, embedder, network, audio-decode or paid-API contact; no Earnings-22 read |
| code | `core.judges.BriefNameNearMissJudge`, `analysis.e21_loop_flags`, `scripts/e21_loop_judge_receipt.py` |
| decision | **none.** This receipt measures an instrument. The cell it prices is `docs/readiness/2026-09-08-e21-loop-1-v1-preregistration.md`, which is preregistered and not authorized to fly |

## The identity anchor, cleared before any precision was computed

The read refuses to publish a precision unless the comparator it decomposed reproduces its own
sealed corpus numbers through this instrument. **10 of 10 checks PASS**: 1,593 windows over 44
calls; S/D/I 13,098 / 5,701 / 10,700 over 359,765 reference words; ConEC PERSON 22.489 % over 2,917
tagged reference words and ORG 17.213 % over 4,363.

## The truth set, and what is deliberately not in it

A **PERSON/ORG substitution** — an alignment operation of kind `OP_SUBSTITUTION` whose reference
word carries a PERSON or ORG entity id. There are **1,253**, spread over **674** of the 1,593
windows.

**PERSON/ORG deletions (154) are counted and reported and are NOT in the recall denominator**, for a
structural reason rather than a convenient one: a deletion consumes no hypothesis word, so no
span-based judge reading a draft can point at one. Insertions never reach an entity bucket at all —
fstalign attributes no insertion to a tag — so they cannot be PERSON/ORG errors by construction.

## Two recalls, and why the second is the one that prices the loop

* **span recall** — the substitution falls *inside* a flagged span;
* **window recall** — the substitution falls in a window the judge flagged **at all**.

The loop contacts a WINDOW, and the Solver hears the whole re-cut and is shown its whole word range.
So window recall is the loop's own ceiling — a substitution in an unflagged window is never
contacted — and span recall is the sharper property of the detector. Both are published, and a
reader who wants "how much of the error mass can this cell reach" wants the second.

| `max_distance` | flagged spans | flagged windows | share of 1,593 | span precision | window precision | span recall | **window recall** |
|---:|---:|---:|---:|---:|---:|---:|---:|
| **0.10** | 100 | 86 | 5.40 % | 49.00 % | 80.23 % | 3.99 % | **14.37 %** |
| **0.15** | 385 | 270 | 16.95 % | 21.30 % | 58.15 % | 6.78 % | **27.13 %** |
| **0.20** **(flown)** | 912 | 534 | 33.52 % | 15.24 % | 53.00 % | 11.65 % | **47.57 %** |
| **0.25** | 2021 | 892 | 55.99 % | 8.31 % | 47.20 % | 14.21 % | **66.08 %** |
| **0.30** | 3053 | 1139 | 71.50 % | 6.22 % | 45.65 % | 15.96 % | **79.25 %** |
| **0.35** | 4530 | 1322 | 82.99 % | 4.72 % | 44.10 % | 17.96 % | **87.95 %** |
| **0.45** | 19503 | 1576 | 98.93 % | 1.61 % | 42.58 % | 26.26 % | **99.60 %** |

## The other two judges, measured rather than assumed

`earnings-numeric-format-flag-v1` fires on **87 of 1,593 windows (5.46 %)**, 123 spans, and its span
precision against a PERSON/ORG substitution is **0.00 %** — as it should be: it asks a numeric question, not a name
question. It is kept in the inventory because a malformed figure is a second reason to hear a window
again, and its base rate is small enough that it costs about five per cent of the budget. Its
precision against a numeric-accuracy MISS is a different measurement, is not made here, and is not
claimed.

`e21-substitution-alignment-flag-v1` fires on **0 of 1,593 windows**. That is not a defect and it is why the measurement was worth making:
on a pass-1 draft its predecessor IS the draft, so it can only report a perfect alignment. It
belongs AFTER the Solve, where its refusal table is the delivery ledger, and that is where the cell
places it — as a reported covariate, never as a flag source. WAVE W1 §5 listed exactly this as
"still to measure".

## The operating point, and the rule that chose it

**The rule was fixed on a gold-free quantity and applied to it**: the operating point is the largest
`max_distance` on the declared ladder whose **flagged-window share** is at most 50 % of the windows
— the budget ceiling the cell's decision rule requires. Flagged-window share needs no reference
transcript, no alignment and no gold of any kind. The precision and recall columns played no part in
the choice; they are published so a reader can see what the choice cost.

That rule selects **`max_distance` = 0.20**: 534 windows for the near-miss judge alone (33.52 %),
which the numeric judge's own 5.46 % bounds above at 38.98 % for the union. The pinned plan measures
the union exactly: **600 units over 44 calls**, **37.66 %** of the 1,593 windows and therefore of
KC-E1f's 1,593 contacts.

For scale, at the judge's own default band (0.25) the inventory would flag 929 windows (58.32 %) and
reach **67.44 %** of the substitution mass — over the 50 % budget ceiling, which is exactly why the
rule exists. At the flown band the near-miss judge alone reaches **47.57 %** of that mass at
**53.00 %** window precision, and the union reaches at least as much.

**Read the two precisions together.** Span precision at 0.20 is 15.24 % and window precision is
53.00 %: four flagged spans in five point at something other than a name error, but a flagged WINDOW
carries a real PERSON/ORG substitution more often than not. The loop spends a contact per window, not
per span, so the second number is the one that prices it — and the first is the honest statement of
how good the pointing is.

## Files

| file | what it holds |
|---|---|
| `judge-receipt.json` | the whole read: the identity anchor, the truth set, per-judge and inventory rates, the distance ladder, the flag-code counts, the contact budget and the per-call block |
| `MANIFEST.sha256` | this directory's byte manifest |

The per-window drafts this read decomposed are per-request derivatives of sealed model outputs and
live under `$SPEECHRL_DATA_DIR` with those outputs; they never enter Git.
