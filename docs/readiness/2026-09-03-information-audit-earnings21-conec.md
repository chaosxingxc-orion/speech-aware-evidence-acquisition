# Earnings21+ConEC dataset information audit (Part B, one template three carriers)

Date: 2026-09-03. Status: model-free-check, zero model/GPU/scorer/embedding/network contact. Ledger
row `SAEA-E21-CONEC-MF-INFORMATION-AUDIT-V1`. Machine artifacts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-information-audit-earnings21-conec/summary.json`
and its `README.md`. Generator: `speech_aware_evidence_acquisition.analysis.information_audit.run_information_audit`
fed `analysis.information_audit_specs.earnings21_conec_spec`. Population: the 44-call
`earnings21-original` discovery split (`data.splits.discovery_split`); 43 of 44 calls carry a usable
entity-mention inventory (section 1 explains the exclusion). Entity-mention gold labels are read from
the already-committed, offline, gold-derived entity inventory under
`$SPEECHRL_DATA_DIR/derived/entity-inventory/v1/` (produced by the existing, unmodified
`scripts/build_entity_inventory.py`), never by importing `data.references` from this study's own new
code -- that import is restricted to `core/scorers.py`
(`tests/contract/test_reference_import_isolation.py`), and `build_entity_inventory.py`'s own module
docstring explains why a `src/` module cannot be the one to read it directly.

## Structural note: knowledge and evaluation coincide

Unlike SLURP/Audio2Tool, Earnings21+ConEC has **no separate construction corpus**. ConEC ships one
context/participant-names/bias-list document PER call, so the "knowledge source" and the "evaluation
roster" are the same 44 calls. Q3 (population distribution) is therefore a census, not a sample, and
Q6 (decontamination) is answered by Q5's own own-call-vs-random-other-call membership contrast, not
a construction-vs-roster identity check (which would trivially show 100% overlap by construction, not
a leakage finding).

## 1. Fields and corpus structures (Q1)

| field | legality |
|---|---|
| sample_id / media_relpath / audio_seconds / sample_rate_hz | runtime-legal-input |
| ConEC context document (`evidence_source=conec-contexts`) | runtime-legal-input |
| ConEC participant-names roster (`evidence_source=conec-names`) | runtime-legal-input |
| ConEC-derived bias list (`evidence_source=conec-bias-list`) | runtime-legal-input |
| wer_tags entity id -> entity_type sidecar | gold-scoring-only |
| entity mention filler text (token join of a wer_tags span) | gold-scoring-only |
| reference transcript tokens (`.nlp`) | **forbidden** |

| corpus structure | legality |
|---|---|
| one ConEC evidence document per call (no shared corpus) | runtime-legal-input |
| earnings21-original confirmatory remainder (beyond the 44-call discovery split) | **forbidden** |
| call `4320211` (pre-existing wer_tags sidecar defect) | gold-scoring-only |

**Known pre-existing data defect (not caused by this study):** call `4320211`'s
`wer_tag.json` sidecar has an entity id (`'1057'`) with no usable `entity_type` --
`data.references.reference_entity_mentions` (called only from the sanctioned
`scripts/build_entity_inventory.py`, section above) refuses that call closed rather than silently
dropping the malformed mention. This audit excludes call `4320211` from every entity-mention-dependent
computation (Q3/Q4/Q5) rather than treating the whole 44-call census as unreadable; every reported
entity-mention population figure below is therefore n=43, not n=44. Q1/Q2 population facts (media
identity, ConEC evidence availability) still cover all 44 calls.

## 2. Task information requirement: OBS / ORG / SUPPLY / USE (Q2)

- **OBS**: transcribe/segment the earnings-call speech into entity-bearing spans, ASR-free at the
  knowledge layer.
- **ORG**: no cross-call retrieval -- ConEC ships one context/names/bias-list document PER call, so
  organization here is selecting WHICH of the three self-supplied documents (or their extraction) to
  expose, not ranking across a corpus.
- **SUPPLY**: expose the call's own ConEC context, names roster, and/or extracted bias-list terms as
  evidence.
- **USE**: the frozen core produces a transcript hypothesis whose entity spans are scored against
  `wer_tags` gold.

## 3. Population (census, not a sample) (Q3)

Strata = call id; the discovery roster IS the full population, so every stratum has count 1 (share
2.33%) by construction -- TVD from natural = 1.0 relative to a hypothetical single-call-dominant
distribution and TVD from uniform allocation = 0.0 (the roster already is the uniform allocation).
This is the expected, honest outcome of a census rather than evidence of a sampling defect: there is
no natural population larger than the 44 calls to deviate from.

## 4. Label-space entropy and prior-mass coverage (Q4)

| label field | labels observed | occurrences (mentions) | entropy (bits) | effective label count |
|---|---:|---:|---:|---:|
| entity_type | 26 / 26 | 37,471 | 3.448 | 10.92 |
| entity_mention (type + normalized filler) | 7,328 / 7,328 | 37,471 | 10.129 | 1,119.99 |

| mass threshold | min k, entity_type | min k, entity_mention |
|---|---:|---:|
| 50% | 3 | 124 |
| 80% | 8 | 1,380 |
| 90% | 10 | 3,581 |
| 95% | 12 | 5,455 |
| 99% | 17 | 6,954 |

At the entity-TYPE grain, 10 of 26 types cover 90% of the 37,471 gold mentions -- a coarse label space
is genuinely learnable from a small set. At the entity-MENTION grain (the actual value to recover, not
just its class), 3,581 of 7,328 distinct surface forms are needed for the same 90% coverage: knowing
the entity TYPE distribution is a poor proxy for knowing which specific company/person/date names will
occur.

## 5. Retrieval reachability (Q5)

Own-call-vs-random-other-call membership over 43 usable calls, 37,469 gold entity mentions (normalized
surface-text substring presence in the call's own concatenated ConEC context + names + bias-list text,
versus a deterministically-paired random OTHER call's text as the negative control):

**Own-context reachability: 30.17%. Random-other-context reachability (negative control): 16.50%.**

| entity type | mentions | own-context | random-other-context |
|---|---:|---:|---:|
| PERSON | 2,163 | 75.91% | 13.45% |
| ORDINAL | 911 | 72.34% | 56.42% |
| GPE | 1,254 | 64.43% | 23.84% |
| ABBREVIATION | 2,323 | 61.82% | 27.08% |
| NORP | 207 | 58.94% | 9.18% |
| ORG | 2,847 | 52.93% | 14.44% |
| CARDINAL | 5,133 | 44.63% | 38.24% |
| LOC | 298 | 45.64% | 8.05% |
| DATE | 6,342 | 17.63% | 13.69% |
| CONTRACTION | 9,008 | 0.53% | 0.72% |
| YEAR | 1,164 | 28.78% | 18.38% |
| MONEY | 1,867 | 34.92% | 32.46% |

(Full 26-type table in the machine README.) Own-context reachability (30.17%) exceeds the random-other
negative control (16.50%) by only ~14 points overall -- ConEC's own supplied evidence genuinely helps
for named-entity classes with low base-rate token overlap (PERSON +62pp, GPE +41pp, ORG +38pp over
random) but the margin nearly vanishes for classes with high base-rate lexical commonality (CARDINAL
+6pp, MONEY +2pp, DATE +4pp) -- for those types, most of what looks like "reachability" is base-rate
token overlap with ANY call's evidence, not this call's evidence specifically. CONTRACTION (0.53% own,
9,008 mentions -- the single largest class) is essentially unreachable from ConEC text at all: it is
overwhelmingly not present verbatim in the supplied evidence documents.

## 6. Decontamination (Q6)

Identity overlap (definitional, not a leakage finding -- see the structural note above): the roster
IS the construction population, so all 43 usable ids overlap by construction.

| roster | construction n | roster n | identity overlap | clean |
|---|---:|---:|---:|---|
| discovery-44 | 43 | 44 | 43 | False (expected -- census, not a sample) |

The substantive Q6 check for this carrier is **cross-call** near-duplicate evidence (template/
boilerplate reuse across different companies' calls, which WOULD be a genuine contamination risk):
token-set Jaccard >= 0.80 over the 43 calls' own concatenated evidence text, all
`43*42/2 = 903` pairs checked -- **0 of 903 pairs** near-duplicate. No two calls in the discovery
roster share a near-identical evidence document.

## 7. External supplementation ledger (Q7)

| need | source | legality |
|---|---|---|
| Company/ticker/person canonical spellings beyond what one call's own ConEC document lists | Another call's ConEC document | **forbidden** (explicitly a negative-control / cross-contamination risk, not a legal supply) |
| A budget-bounded distillation of the raw ConEC context to fit prompt budgets | `core.bias_lists.extract_bias_candidates` / `reconstruct_bias_phrases` over the SAME call's own context | runtime-legal-input |

## 8. Power (Q8)

Two-sided McNemar test, alpha=.05, target power=80%, paired-binomial normal approximation, using the
same two sealed SLURP DEV-ladder discordant-pair rates as the empirical basis (Earnings21+ConEC has no
sealed paired verdict of its own yet at the 44-call discovery scale -- this is a cross-task-borrowed
rate, not an Earnings-specific measurement, and should be read as such):

| citation | n | discordant rate | source |
|---|---:|---:|---|
| DEV-500 confirmatory (400 unexposed) | 400 | 20.75% | `docs/readiness/2026-08-24-dev500-confirmatory-verdict.md` |
| DEV-1000 baseline lock (500 unexposed) | 500 | 22.20% | `docs/readiness/2026-08-25-baseline-lock-verdict.md` |

Minimum detectable paired accuracy delta (percentage points), call-level (n=44, the official
`asr-wer` scorer's own natural unit) versus mention-level (n=37,469, if a paired comparison is scored
per gold entity mention rather than per call):

| n (unit) | MDE using DEV-500 rate | MDE using DEV-1000 rate |
|---|---:|---:|
| 44 calls | 19.24 pp | 19.90 pp |
| 37,469 entity mentions | 0.66 pp | 0.68 pp |

At the call level, only a very large (~19-20 pp) paired accuracy effect is detectable at 80% power --
the 44-call discovery roster is a coarse instrument for a whole-call metric. At the entity-mention
level the same n gives essentially unconstrained power (<1 pp MDE): if the eventual scorer is
entity-level (matching the existing `entity-wer` scorer's own per-mention granularity, `core.scorers.
score_entity_wer_outputs`), statistical power is not the binding constraint -- the 44-call population
itself, and its own coverage of entity types/mentions (section 4), is.

## What this changes for the experiment plan

Three findings should shape how ConEC evidence is used next. First, own-context reachability (30.17%)
only modestly beats the random-other-call base rate (16.50%) in aggregate -- roughly half of the
apparent "reachability" signal is generic lexical commonality, not real evidence value, and the useful
margin concentrates in named-entity classes (PERSON/GPE/ORG/ABBREVIATION/NORP), not in
high-frequency generic classes (CONTRACTION/DATE/CARDINAL/MONEY). A future evidence-quality metric
should report the own-vs-random DELTA per entity type, not own-context reachability alone. Second,
CONTRACTION mentions (24% of all gold mentions, the single largest class) are essentially unreachable
from ConEC text (0.53%); no supply-side change to ConEC exposure will move this class, and it should
not be counted against a future evidence-supply mechanism's own ceiling. Third, if the eventual
paired confirmatory read is scored at the CALL level, only large (double-digit-pp) effects are
statistically detectable at n=44; scoring at the entity-mention level removes that constraint almost
entirely, so scorer granularity should be decided before, not after, a 44-call paired comparison is
preregistered.

## Artifacts

- Machine summary: `docs/checks/speech-aware-evidence-acquisition/2026-09-03-information-audit-earnings21-conec/summary.json`
- Machine README: `docs/checks/speech-aware-evidence-acquisition/2026-09-03-information-audit-earnings21-conec/README.md`
- Generator: `src/speech_aware_evidence_acquisition/analysis/information_audit.py` (`run_information_audit`)
- Spec builder: `src/speech_aware_evidence_acquisition/analysis/information_audit_specs.py` (`earnings21_conec_spec`)
- Ledger row: `docs/exposure-ledger.md`, `SAEA-E21-CONEC-MF-INFORMATION-AUDIT-V1`
- Entity inventory cache (pre-existing tool, invoked read-only for the 44-call discovery split):
  `scripts/build_entity_inventory.py`, output under `$SPEECHRL_DATA_DIR/derived/entity-inventory/v1/`
