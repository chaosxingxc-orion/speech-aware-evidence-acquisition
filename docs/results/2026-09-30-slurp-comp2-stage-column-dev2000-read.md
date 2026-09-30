# COMP-2 stage-column read on cell A2 (DEV-2000-ADDED): the scope rule adds official SLU-F1 +0.49 pp CI95 [-0.01, +1.00] on the arm and +0.73 [+0.25, +1.23] on the A/A replicate; FAILS Q2 at the 1.5485 bar; the composed COMP-2 contrast vs the A/A is intent +4.60, SLU-F1 +1.02 [-0.64, +2.68] (DESCRIPTIVE)

Read on 2026-09-30 by the records and read agent (Claude Opus 5.5, on the coordinator's brief, Fable 5.1), in
worktree `fable/comp2read`.

The READ row `SAEA-SLURP-STAGE3-COMP2-STAGE-COLUMN-DEV2000-READ-V1` was root countersigned on master at `aaf4f2f93`
(2026-09-30T06:09:30Z). That was after both A2 seals and before any stage-column score was opened (owner decision
203).

The driver is `python -B scripts/analysis/slurp_comp2_stage_column_read.py --preset a2 --none-hint`. It ran in WSL
from master and exited 0, leaving the tree clean.

Contacts: no model, server, tokenizer, encoder, embedder, network or GPU contact, and exactly 2 official scorer jobs
(one per stage column, through `core.scoring_batch.score_complete_derived_copy`). The delivered columns were not
re-scored; their sealed official per-sample scores were read.

**DESCRIPTIVE.** These are development numbers on DEV-2000-ADDED (owner decisions 28 and 86). They are never a test
claim, and nothing is admitted by this note. No utterance text, filler, gold value or model output was printed or
persisted.

## 1. Inputs

| column | source | official intent | official SLU-F1 | bytes |
| --- | --- | ---: | ---: | --- |
| arm delivered | `SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1` (sealed) | 81.50 | 65.93 | outputs `25e6dd9d...`, scores `878babaa...` |
| arm + scope rule | stage column | 81.50 | 66.42 | `columns/arm-scope-rule-stage.jsonl` `36cbc7e1...` |
| A/A delivered | `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1` (sealed) | 76.90 | 65.40 | outputs `016b09dc...`, scores `0543d025...` |
| A/A + scope rule | stage column | 76.90 | 66.13 | `columns/aa-scope-rule-stage.jsonl` `b566472d...` |

- **The stage.** `saea-deliver-scope-rule-v1`, version 1, with pinned table
  `prepared/SAEA-SLURP-SCOPE-RULE-TABLE-V1/table-v1.json` (`fcff0c42...`).
- **Output and bootstrap.** The report is `analysis/SAEA-SLURP-STAGE3-COMP2-STAGE-COLUMN-DEV2000-READ-V1/report.json`
  (sha256 `335316d9...69240`), with render manifest `af0ea882...`. The bootstrap is
  `analysis.bootstrap.paired_cluster_bootstrap`: unit roster row, 10,000 draws, seed 20260929, CI95.

## 2. Contrasts

| contrast | intent delta pp | intent CI95 | SLU-F1 delta pp | SLU-F1 CI95 | intent rows changed |
| --- | ---: | --- | ---: | --- | ---: |
| **stage column vs delivered (arm), the stage's own effect** | 0.00 | [0.00, 0.00] | **+0.49** | **[-0.01, +1.00]** | 0 |
| A/A replicate: A/A stage column vs A/A delivered | 0.00 | [0.00, 0.00] | +0.73 | [+0.25, +1.23] | 0 |
| **composed COMP-2: arm stage column vs A/A delivered** | **+4.60** | **[+2.60, +6.60]** | **+1.02** | **[-0.64, +2.68]** | 112 |
| reference, COMP-1b: arm delivered vs A/A delivered | +4.60 | [+2.60, +6.60] | +0.53 | [-1.01, +2.12] | 112 |

- **Bootstrap unit.** The reference row repeats the A2 gating contrast on this script's bootstrap unit (roster row).
  The A2 read's registered unit is utterance cluster, and it gave intent [+2.58, +6.73] and SLU-F1 [-1.04, +2.09].
- **Intent.** The stage leaves intent unchanged by construction, and the check confirms 0 rows changed.
- **Rows and entities.** The stage edits 61 arm rows and drops 64 entities. On the A/A it edits 62 rows and drops 65
  entities.

**Dropped entities, split against gold offline.**

| column | dropped | spurious (no gold match) | exact gold match | other |
| --- | ---: | ---: | ---: | ---: |
| arm | 64 | 37 | 5 | 22 |
| A/A | 65 | 40 | 5 | 20 |

On the arm, the largest classes are person (12: 10 spurious, 1 exact, 1 other), definition_word (8: 6 / 0 / 2),
event_name (6: 4 / 0 / 2), list_name (6: 2 / 1 / 3), date (5: 0 / 0 / 5) and media_type (4: 4 / 0 / 0).

**Per scenario (arm, stage column minus delivered, official SLU-F1).** The scenario labels come from the governed
DEVEL loader, offline.

| scenario | rows | rows edited | delta pp |
| --- | ---: | ---: | ---: |
| calendar | 221 | 13 | +0.48 |
| play | 203 | 10 | +0.91 |
| qa | 157 | 11 | +0.34 |
| email | 96 | 8 | +0.63 |
| weather | 65 | 2 | +0.78 |
| general | 62 | 4 | -1.66 |
| iot | 57 | 4 | -1.14 |
| lists | 52 | 5 | -2.35 |
| transport | 48 | 1 | +0.57 |
| news | 20 | 1 | +2.13 |
| datetime | 9 | 2 | -5.58 |
| recommendation | 6 | 0 | 0.00 |
| social | 4 | 0 | 0.00 |

The natural-mixture delta is +0.49 pp and the equal-scenario delta is -0.38 pp. On the A/A they are +0.73 and +0.20.

**None hint (decision 199, trigger coverage only, gold-free; this read edits no row for it).**

- 1,000 rows have supply, with 0 unresolved exemplar ids.
- 51 rows trigger (entity-free exemplar share >= 0.6).
- 17 of the triggered rows delivered at least one entity, 18 entities in all.

## 3. The Q2 verdict

The rule (E5 spec, coordinator ruling) has three legs:

- the stage's own SLU-F1 CI95 must exclude zero;
- its point must be at least 1.49 * sqrt(1080 / 1000) = **1.5485 pp**;
- the A/A replicate must show the same sign at >= 1.0 pp.

| leg | value | met |
| --- | --- | --- |
| own CI95 excludes zero | [-0.0118, +1.0017] | no (the lower bound is 0.01 pp below zero) |
| own point >= 1.5485 | +0.4899 | no |
| replicate same sign >= 1.0 pp | +0.7314 (same sign, CI95 [+0.25, +1.23]) | no (under 1.0) |

**Verdict: FAILS-Q2**, with all three legs unmet.

**Read agent's summary, for the coordinator.**

- **Direction.** The scope rule moves SLU-F1 upward on both columns: +0.49 on the arm and +0.73 on the A/A, where the
  replicate's interval excludes zero.
- **Size.** It edits about 6 % of rows, and the drops are majority spurious (37 of 64 on the arm). The effect is a
  third of the Q2 bar.
- **The composed contrast.** COMP-2 against the A/A is intent +4.60 [+2.60, +6.60] with SLU-F1 +1.02 [-0.64, +2.68].
  That is +0.49 pp SLU over COMP-1b's +0.53 in the same unit, and it does not change the A2 verdict class.
- **Scenario pattern.** The equal-scenario delta is negative (-0.38) because small scenarios lose: datetime (n = 9),
  lists and general.

On the registered Q2 bar, the scope rule does not qualify as a COMP-2 component on DEV-2000-ADDED.

## 4. Reproduce

```bash
# model-free (two official scorer jobs); master after the READ-row countersignature (aaf4f2f93); in WSL
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B scripts/analysis/slurp_comp2_stage_column_read.py --preset a2 --none-hint
```

The driver refuses to overwrite an existing complete read. The outputs are under
`analysis/SAEA-SLURP-STAGE3-COMP2-STAGE-COLUMN-DEV2000-READ-V1/`: `columns/`, `scores/`, `render-manifest.json` and
`report.json`.

## Coordinator verdict (Fable 5.1, 2026-09-30)

- **Scope rule on A2: FAILS Q2, not included in COMP-2.** Stage column vs delivered +0.49 [-0.01, +1.00] (61 rows, 64 entities dropped, 37 spurious) against the 1.5485 bar; replicate +0.73 [+0.25, +1.23]; the Fold A rehearsal's +1.35 shrank on DEV. COMP-2 as declared under decision 203 is therefore COMP-1b alone; the scope rule stays a registered deliver stage (no-harm form step) and re-enters only inside a later composed read, never as its own claim. The none hint triggered on 51 rows (17 with delivered entities): inner-loop knob only.
