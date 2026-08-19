# P-PHON — failure-class decomposition of supply conversions — REGISTERED

Date: 2026-08-18. Status: **REGISTERED — executable once the suite extension lands and is
reviewed** (model-free re-read; zero GPU, zero core contact). Profile: `model-free-check`.
Owner GO: 2026-08-18 ("基本认可" of the coordinator's speech-term program; this is probe ①).
Purpose: first evidence on the study's identity question — **does speech knowledge
participate in the supply loop, or is the audio only a retrieval key?** — by asking WHICH
KIND of failure supply converts.

## 1. Classes (mechanical, pinned; computed on gold-vs-A0-predicted VALUE strings,
scoring-side only)

Per failed slot/argument of the zero-supply baseline:
- **MISSING** — no value emitted for the gold slot.
- **EQUIV-FORMAT** — equal after the pinned normalization (casefold, strip
  punctuation/whitespace, digit↔word map, article strip) — content right, label space wrong.
- **NEAR-MISS** — normalized Levenshtein ≤ 0.5 after normalization — the orthographic proxy
  for an acoustically proximate mishearing (honestly named a PROXY; P-KEY is the decisive
  instrument).
- **FAR-WRONG** — everything else.

## 2. Scope

- **SLURP** (primary; gold devel transcripts exist scoring-side): the consumed parent
  attempt (A3 = primary supply arm; A1/A4 descriptive) and the consumed s2 attempt (A1'r).
  Per class: baseline failure counts, supply-converted counts, class conversion rate CR(c).
- **A2T** (secondary, orthographic proxy only): the consumed A0/S-arm/B-arm/C-arm attempts;
  same classes on argument values (B1/C1/C2 as the clean-form conversion set).

## 3. Verdicts (primary on SLURP-A3; A1'r must be reported as concordant/discordant)

- **SPEECH-SNAP-PRESENT**: NEAR-MISS conversions ≥ 25% of all conversions AND
  CR(NEAR-MISS) ≥ CR(FAR-WRONG) + 0.15 — supply preferentially repairs acoustically
  proximate mishearings ⇒ the roster acts as a perceptual disambiguation prior, not only a
  recall bank.
- **FORMAT-DOMINANT**: EQUIV-FORMAT conversions ≥ 60% of all conversions — the L3 gain is
  mostly label-space alignment; the speech term is not in evidence here.
- Otherwise **MIXED** (full table; no flag).
These may NOT co-fire by construction (25%+ NEAR vs 60% FORMAT can co-occur only if
conversions ≥ 85% split exactly — if both fire, report BOTH, flag the boundary case).
Thresholds are first-pass descriptive calibrations and are recorded as such; the decisive
instrument for the key-vs-knowledge question is the registered P-KEY factorial (probe ②).

## 4. Discipline

Registered RE-READ of consumed attempts (loss-decomp precedent): originals stay consumed
and untouched; new instrument `analysis/pphon_decomp.py` + CLI reuses the consumed suites'
value-alignment primitives verbatim; inputs MANIFEST-verified; suite built and
coordinator-reviewed BEFORE execution; one execution, idempotence-guarded output dir
`docs/checks/speech-aware-evidence-acquisition/2026-08-18-pphon-decomp/`; exposure row
`SAEA-CHECK-pphon-decomp` appended at registration (consumed=no; flips at the read).
Zero core contact, zero GPU. Gold transcripts/values touched scoring-side only (never any
prompt path). CC BY-NC 4.0 carried from both carriers.
