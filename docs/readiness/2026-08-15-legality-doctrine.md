# Legality & provenance doctrine (D2, 2026-08-15; provenance schema per review wf_c21a2756)

Owner-derived three-dimension doctrine, now the design-review standard for every arm.

## The three dimensions

1. **Gold red line.** Gold/reference transcripts, test annotations, and ANY derivative —
   including gold-guided SELECTION of terms, spans, references, or exemplars — never enter
   the runtime path of a deployment-tier arm. Selection is a leakage channel equal to
   content (precedent: the SAEA-SMOKE-mapflip round-c withdrawal).
2. **System capability is not cheating.** Anything a system module computes AT INFERENCE
   TIME from legal inputs (audio, own drafts, call metadata, pinned documents, the KB, a
   front model's analysis) is legal knowledge. The control plane IS the research object;
   its internal products are admissible everywhere.
3. **Deployment-shaped matching.** The query direction must mirror deployment: speech (or
   its system-derived products) queries the knowledge base. Keying granularity is bounded
   by what deployment truly holds: call identity — yes; which in-call terms/spans matter —
   must be earned by the system's own matching, never by dataset construction.

## Per-arm provenance schema (MANDATORY for every targeted-delivery registration)

Every targeted-delivery arm declares two fields in its ledger row and result tables:

- `span_source`: `gold-aligned` (= CEILING tier) | `roster-band-flag` or another
  system-computed flag (= legal tier)
- `reference_source`: `p1-oracle-v1`-lineage or any gold derivative (= CEILING tier) |
  ConEC call-keyed document via S1 matching / metadata roster / pinned tier-3
  materialization / own-draft product (= legal tier)

EITHER field gold-derived makes the whole arm **ceiling-tier** ("ceiling instrument only,
never a method" — the p1-oracle-v1 wording is the precedent and stays mandatory). Tier
labels appear in the registration, every result table, and every verdict. Ceiling-tier
arms read against ceiling anchors (names 10.88 lineage) for operator-vs-operator
conclusions ONLY; legal-tier arms read against zero 12.38 / metadata 12.09.

## Named traps (measured or review-caught)

- Recasing the ConEC lowercase word lists from gold transcripts or the oracle roster is a
  gold derivative. Legal casing sources: call-metadata fields, pinned pre-fetched issuer
  documents, or the frozen core's own truecasing of the list (dimension-2 system product).
- The wrong-reference control arm certifies audio-verification vs text-following ONLY; it
  cannot certify selection legality — only the provenance fields do.
- "No new sample identity" boilerplate in ledger rows does not extend to new carriers
  (Audio2Tool, SLURP, SlideASR): each new carrier needs its own split identity registration
  before first touch.
