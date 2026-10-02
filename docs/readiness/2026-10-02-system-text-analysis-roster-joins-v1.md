# System-text analysis roster joins

Owner214 registers TRAIN feedback/selection within one system-text search sequence.
These analysis-only receipts project the already frozen selection lists into the
shared roster reader's item schema. They do not change the original selection,
source role, runtime view, current recipe or model-facing context.

## Prepared bindings

| Stage | Original cohort | Rows | Analysis receipt |
|---|---|---:|---|
| Update1 | TRAIN Fold A positions1-400 | 400 | `../receipts/rosters/slurp-system-text-update-1-400-analysis-v1.json` |
| Update2 | TRAIN Fold A positions401-800 | 400 | `../receipts/rosters/slurp-system-text-update-2-400-analysis-v1.json` |
| Update3 | TRAIN Fold B positions1-400 | 400 | `../receipts/rosters/slurp-system-text-update-3-400-analysis-v1.json` |
| Selection | TRAIN Fold B positions401-800 | 400 | `../receipts/rosters/slurp-system-text-selection-400-analysis-v1.json` |

The `construction` role describes the exact approved optimization/selection
exposure for the shared reward-link reader. It does not authorize runtime targets
or new knowledge-construction contacts. No original evaluation receipt was
relabeled. DEV and test are not included. Final selection feedback must not
re-enter proposal generation, and blind proposer inputs remain result-free.

## Verification

Reproduced the registered stable-hash selection with `build_protocol`. Verified
all source/selection/runtime-view file hashes, exact ordered membership and split
identities through `core.roster.write_roster` and `read_roster`. Each cohort has
400 distinct sample and utterance identities; all pairs are disjoint at both
levels. Each item contains only sample ID, utterance ID, audio duration and headset
flag. Labels, transcripts, strata, task outputs and quality values are absent.

The provenance receipt pins the current owner217 protocol, original runtime-view
receipt and all four output files. No task-quality read, model, tokenizer or scorer
contact occurred. This metadata preparation adds no READ or dispatch authority.

## Use after completion

Bind the appropriate receipt's exact file hash as `construction_roster` when
building the complete family's reward-link artifacts. First verify every admitted
member's finalization, seal and unique successful official score, then countersign
the exact root READ. Do not publish incomplete feedback or select a parent early.
Recheck each new candidate's cumulative sources against its prospective roster;
these fixed joins are not a substitute for transitive exposure isolation.
