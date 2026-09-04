# SLURP dataset information audit (Part B, one template three carriers)

Date: 2026-09-03. Status: model-free-check, zero model/GPU/scorer/embedding/network contact. Ledger
row `SAEA-SLURP-MF-INFORMATION-AUDIT-V1`. Machine artifacts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-03-information-audit-slurp/summary.json` and
its `README.md`. Generator: `speech_aware_evidence_acquisition.analysis.information_audit.run_information_audit`
fed `analysis.information_audit_specs.slurp_spec`. Construction population: 11,514 TRAIN utterances
(`SlurpTrainMaterial`); evaluation rosters: the DEV-100/500/1000 ladder receipts under
`docs/receipts/probe-samples/`. Devel/test sentence TEXT is never read by this audit -- only
identity (utterance number) and each roster's own already-committed `scenario_allocation`/
`selection_rule` metadata, following the identity-only decontamination discipline
`docs/receipts/knowledge/slurp-split-identity.json`'s own generator already established.

## 1. Fields and corpus structures (Q1)

| field | legality |
|---|---|
| scenario | runtime-legal-input |
| sample_id / utterance_id / media_relpath | runtime-legal-input |
| audio_seconds | runtime-legal-input |
| action | gold-scoring-only |
| intent (scenario_action) | gold-scoring-only |
| entities (type + filler span) | gold-scoring-only |
| train sentence text (`SlurpTrainMaterial.sentence`) | construction-only-knowledge |
| train speaker_id | construction-only-knowledge |
| devel/test sentence text | **forbidden** |

| corpus structure | legality |
|---|---|
| utterance (one or more recordings sharing one sentence/scenario/action/entities) | construction-only-knowledge |
| `train_synthetic` split | **forbidden** (64.8% verbatim overlap with `devel` -- `data.slurp.load_slurp_ontology`'s own docstring finding, cited here, not re-derived: this audit never opened `train_synthetic.jsonl`) |
| `test` split | **forbidden** |

`SlurpRecord` (the runtime-legal type) deliberately carries no sentence field at all -- the loader's
own module docstring records this as a scope choice, not an oversight: the five `TaskAdapter` methods
and scoring never need it, and reading it here would blur the OBS boundary this audit is auditing.

## 2. Task information requirement: OBS / ORG / SUPPLY / USE (Q2)

- **OBS**: perceive the spoken command from AUDIO only; recover scenario/action/entity-bearing spans
  without a reference transcript (`SlurpRecord` at runtime carries no sentence field).
- **ORG**: multi-dimensional key retrieval (content/speaker/label/prior) over the TRAIN-modeled
  knowledge base; a ranking policy fuses dimensions -- the Q-K-V doctrine,
  `docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md` section 1.
- **SUPPLY**: consume retrieved TRAIN-derived value cards (scenario/action exemplars, entity-type
  fillers) as priors, sample-linked, never embedded as ground truth.
- **USE**: the frozen core commits to one `scenario_action` intent and a set of `(type, filler)`
  entity slots per utterance.

## 3. Natural population distribution and roster deviation (Q3)

Natural (TRAIN) scenario distribution ranges from 1.83% (`cooking`) to 14.66% (`calendar`) across 18
scenarios -- not close to uniform. Every DEV-* roster is drawn **scenario-stratified, as evenly as
the eligible pool allows** (each roster's own `selection_rule`, read directly from its committed
receipt, never re-derived by reading devel text):

| roster | intended n | TVD from natural | TVD from uniform allocation | classification |
|---|---:|---:|---:|---|
| DEV-100 | 100 | 0.2385 | 0.0444 | near-equal-stratum |
| DEV-500 | 500 | 0.2391 | 0.0062 | near-equal-stratum |
| DEV-1000 | 1000 | 0.2155 | 0.0652 | near-equal-stratum |

All three DEV-ladder rosters are **equal-stratum stress rosters, not samples of the natural TRAIN
mixture** -- a scenario's DEV-ladder share is not evidence of its true call-volume share. `calendar`
(14.66% of TRAIN) and `cooking` (1.83% of TRAIN) both land near 5-6% of any DEV tier.

## 4. Label-space entropy and prior-mass coverage (Q4)

| label field | labels observed | occurrences | entropy (bits) | effective label count |
|---|---:|---:|---:|---:|
| intent (scenario_action) | 60 / 60 | 11,514 | 5.412 | 42.57 |
| entity_type | 55 / 55 | 10,974 | 4.643 | 24.99 |

| mass threshold | min k, intent | min k, entity_type |
|---|---:|---:|
| 50% | 12 | 6 |
| 80% | 31 | 18 |
| 90% | 40 | 26 |
| 95% | 47 | 33 |
| 99% | 55 | 43 |

Both label spaces are meaningfully harder to prune than a small closed set: reaching 90% prior mass
still needs 40 of 60 intents or 26 of 55 entity types. A frequency-only prior cannot safely shrink
either registry the way a handful of high-frequency labels might suggest at a glance.

## 5. Retrieval reachability (Q5)

Label-blind, grouped (utterance-id / normalized-text / BM25-token-twin), 5-fold, TRAIN-internal BM25
coverage over the union of 115 registered labels (60 intents + 55 entity types -- matches the KB
build receipt's own `selected_intents`/`selected_entity_types` counts exactly, `docs/receipts/
knowledge/slurp-kb-size-full.json`), scored on all 11,514 utterances out-of-fold:

| k | full-set coverage | label recall | mean distractors | worst-fold full-set |
|---:|---:|---:|---:|---:|
| 5 | 79.80% | 87.11% | 3.30 | 78.72% |
| 16 | 94.30% | 96.66% | 14.11 | 93.92% |
| 32 | 97.64% | 98.69% | 30.07 | 97.09% |
| 64 | 99.17% | 99.53% | 62.06 | 98.83% |

This is a construction-internal, perfect-transcript-text ceiling on lexical (BM25) retrieval of the
required intent+entity-type label set from TRAIN sentence text -- it says nothing about runtime
recovery from AUDIO, which has no transcript at all. At k=16 (a plausible knowledge-card budget) the
lexical channel already reaches 94.30% full required-set coverage with a 14.11 mean-distractor
budget; k=5 leaves one in five utterances missing at least one required label.

## 6. Decontamination (Q6)

Identity-only overlap between TRAIN (construction) and every DEV-ladder roster (utterance-number
identity; devel/test text is never opened, matching `slurp-split-identity.json`'s own discipline):

| roster | construction n | roster n | identity overlap | clean |
|---|---:|---:|---:|---|
| DEV-100 | 11,514 | 100 | 0 | True |
| DEV-500 | 11,514 | 500 | 0 | True |
| DEV-1000 | 11,514 | 1000 | 0 | True |

Zero overlap on every roster, as expected for SLURP's own train/devel split design. This audit does
**not** attempt a near-duplicate TEXT check against devel (Q6's other named metric) because doing so
would require reading devel sentence text, which this audit deliberately never opens (section 1); the
existing KB-build decontamination receipt (`docs/receipts/knowledge/slurp-kb-size-full.json`,
`decontamination.verdict: "clean"` over 50,628 checked samples against the frozen split-identity
receipt) is the citable authority for that broader check and is not re-derived here.
`train_synthetic` is separately excluded from ANY roster this audit reads (section 1) because it
recurs verbatim in 64.8% of devel -- reported from the existing loader's own documented refusal, not
re-measured.

## 7. External supplementation ledger (Q7)

| need | source | legality |
|---|---|---|
| A user/domain ontology of legal scenario/action/entity-type names | `data.slurp.load_slurp_ontology` (mined from `train` only, `include_synthetic=False`) | construction-only-knowledge |
| Entity-type example fillers for value-card construction | The KB build (`slurp-kb-distmodel-v1`) TRAIN-modeled datastore, decontaminated vs devel/test | construction-only-knowledge |
| A larger action-support pool for long-tail scenarios/entities | The T500 train-side discovery tier (approved in principle, `2026-08-23-knowledge-plane-baseline-rulings.md` section 2) | construction-only-knowledge |

## 8. Power (Q8)

Two-sided McNemar test, alpha=.05, target power=80%, paired-binomial normal approximation
(`analysis.information_audit.minimum_detectable_paired_effect_pp`), using the two sealed SLURP
DEV-ladder paired verdicts as the empirical discordant-pair-rate basis:

| citation | n | discordant rate | source |
|---|---:|---:|---|
| DEV-500 confirmatory (400 unexposed) | 400 | 20.75% (W→C 81 / C→W 2) | `docs/readiness/2026-08-24-dev500-confirmatory-verdict.md` |
| DEV-1000 baseline lock (500 unexposed) | 500 | 22.20% (W→C 106 / C→W 5) | `docs/readiness/2026-08-25-baseline-lock-verdict.md` |

Minimum detectable paired accuracy delta (percentage points) at each DEV-ladder tier's intended n:

| roster | intended n | MDE using DEV-500 rate | MDE using DEV-1000 rate |
|---|---:|---:|---:|
| DEV-100 | 100 | 12.76 pp | 13.20 pp |
| DEV-500 | 500 | 5.71 pp | 5.90 pp |
| DEV-1000 | 1000 | 4.04 pp | 4.17 pp |

DEV-100 is powered only for large (double-digit-pp) effects; DEV-500/DEV-1000 reach single-digit-pp
sensitivity, consistent with the actually-observed sealed effects (+19.75pp and +20.20pp) landing
comfortably inside the detectable range at both tiers.

## What this changes for the experiment plan

Nothing here overturns a prior decision, but three facts should shape the next knowledge-plane
iteration. First, both label spaces (intent and entity_type) need k >= 16 before lexical retrieval
clears 94% full-set coverage; a k <= 5 knowledge-card budget will systematically miss required labels
on roughly one in five utterances, independent of any downstream ranking improvement. Second, every
DEV-ladder roster is an equal-stratum stress design, not a natural-mixture estimate -- a scenario-level
win/loss breakdown on DEV-100/500/1000 should never be read as a call-volume-weighted estimate without
reweighting by the TRAIN shares in section 3. Third, DEV-100 alone is underpowered for anything but a
large directional signal (MDE ~13pp); a DEV-100-only null result should not be treated as evidence of
"no effect" the way a DEV-500/1000 null result more nearly could be.

## Artifacts

- Machine summary: `docs/checks/speech-aware-evidence-acquisition/2026-09-03-information-audit-slurp/summary.json`
- Machine README: `docs/checks/speech-aware-evidence-acquisition/2026-09-03-information-audit-slurp/README.md`
- Generator: `src/speech_aware_evidence_acquisition/analysis/information_audit.py` (`run_information_audit`)
- Spec builder: `src/speech_aware_evidence_acquisition/analysis/information_audit_specs.py` (`slurp_spec`)
- Ledger row: `docs/exposure-ledger.md`, `SAEA-SLURP-MF-INFORMATION-AUDIT-V1`
