# MF-8 — the speech-to-knowledge audit: pricing the three-dimension direction (2026-09-08)

Row id `SAEA-SLURP-MF8-SPEECH-TO-KNOWLEDGE-AUDIT-V1`, profile `model-free-check`.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-08-mf8-speech-to-knowledge-audit/`.
**Zero model contacts, zero GPU, zero tool, zero embedding, zero network, zero audio decode.**

## 0. What this audit is for

The owner's 2026-09-08 direction: *AI should understand audio intent directly; explore how
(multi-speaker) speech maps onto already-constructed knowledge in three dimensions —*

1. **text-domain knowledge** — the gold TRAIN text of an exemplar utterance;
2. **speech-domain knowledge** — *the same speaker's* semantically diverse expressions of one
   intent, as audio;
3. **state knowledge** — what a home assistant legitimately holds before the utterance, the part
   that raises business performance.

This note prices that direction before anything is preregistered. It answers five questions with
numbers and cites the source of every one. **It admits nothing, promotes nothing, and does not
preregister a cell.** Every cell sketched in section 5 is a *price*, not a registration.

## 0.1 Boundary, stated before the first read

* The held-out `test` split is never named, loaded, hashed or scored.
* **DEV sentence text is never read.** Only DEV *gold intent labels* enter, and only to COUNT
  exemplar availability and to attribute comparator errors. No runtime design in this note may
  read a DEV gold label; the availability counts are an audit statistic about the corpus, not a
  mechanism input, and section 5 states for each priced arm what it would be allowed to see.
* TRAIN gold text is read as **knowledge inventory** — it is construction data under the study's
  split-usage philosophy, and it is already the source of every knowledge receipt in this repo.
* No new speech identity opens. Every DEV-1000 row here has already been contacted; every TRAIN
  utterance read here is already inside the sealed knowledge-build closure.
* Audio *headers* (frame count, sample rate) may be read for duration arithmetic; **no audio
  sample is decoded** and no waveform is opened.

## 1. Speaker structure — PENDING

## 2. Where the comparator fails — PENDING

## 3. Multi-audio prompt feasibility — PENDING

## 4. State knowledge inventory — PENDING

## 5. The priced cell family — PENDING
