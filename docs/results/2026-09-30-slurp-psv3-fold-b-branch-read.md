# Cell P-SV-3 (same-flight Perception branch, boundary depth 8 -> 12) branch read: b-depth vs a-agree gold-on-list -1.39 pp CI95 [-2.31, -0.56] against a twin present bar of 1.02 pp; level-2 intent 0.00, official SLU-F1 +0.01 pp [-0.42, +0.44] beside, on TRAIN Fold B (DESCRIPTIVE)

Read 2026-09-30 (UTC; outputs generated 02:00Z to 02:09Z) by Claude Opus 5.5 (records and read agent, on the
coordinator's brief, Fable 5.1) in the worktree `fable/psv3read` (model-free; `core.flight.cli` and `lease_cli` were
not invoked; no GPU, model, server, encoder or tokenizer contact; three official column scorings). READ row
`SAEA-SLURP-STAGE3-PSV3-FOLD-B-BRANCH-READ-V1` was root countersigned 2026-09-30T01:59:51Z (master `1247cf33a`),
after the seal (arm-inspect PASS and step-done 2026-09-30T01:58:55Z) and before any branch column score existed.
Recipe `docs/readiness/2026-09-29-slurp-stage3-psv3-fold-b-v1/analysis-recipe-v1.json` (sha256
`319f4e755fbef7935012e26f9aabf1cae1b07021f00d269f8b56b2c448528602`), recipe id
`slurp-stage3-psv3-fold-b-branch-analysis-v1`, rule kind `presence`. Paired row bootstrap, cluster key
`sample_id`, 10,000 draws, seed 20260929, TRAIN gold through the governed loader and
`slurp-slu-official-train`. Owner decisions 184 (the read form) and 200 (the boundary-depth branch).

The driver was `scripts/flights/psv/psv_read.sh psv3` (run once, rc 0, with `SAEA_REPO_ROOT` pointed at this
worktree; a `--dry-run` preceded it; no `--rescore`). It called `scripts/analysis/slurp_perception_branch_read.py`
(sha256 `499598f3726f97e2050c1d2bd8424afe2ab943be3e45376e91a71de3ddbe626e`).

Outputs under `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-PSV3-FOLD-B-BRANCH-READ-V1/`:

- receipt `perception-branch-read.json` (schema `saea-perception-branch-read-v1`) sha256
  `0e068f25b340a4810be76a9f5b5fb7dc711b26d9433feeb55c5cf43b75af2c3c`;
- `twin-null/`: `verdict.json` `3e23332f0612dc13d7c6252ac76be77bb0b06c0587b4dca1d55601d66b5eabe0`,
  `score-contrasts.json` `f3027854249be9d606c3630f0e175b51c6e44acdcf7ebd3d5f509d564c42e34c`,
  `per-scenario-tables.json` `278eca464909395ae802aa5c265214a2bdf82bc8b632440e439dccaa1835d628`;
- `branch/`: `verdict.json` `2a20858faa99b56c7c94a35ed1dfd9ab6c267dd244cd8375a37ea4f785315306`,
  `score-contrasts.json` `e2bc68ebdfd4bdbe7bddc6640067c6b62ffe0a53d3fcdc1570cd8cb68e1387d5`,
  `per-scenario-tables.json` `e390d0e6db13d8c641b67a4fc6b0736b757a451a42871097feef05a343eec0aa`;
- the three column scorings: `supply-variants/score-summary.json` under the sealed attempt, sha256
  `700e122416e741febcd9e5ba2aa12e8d613756fb75e057290a3815f5579eb972`.

The supplied-item and prompt-token counts in section 1 come from a read-only pass over the sealed trace. That pass
counted items and read `usage.prompt_tokens` only, the method of `scripts/flights/psv/psv_fit_measure.py`, and
persisted nothing.

No utterance text, gold label, slot filler, note text or model output was printed or persisted. Only counts,
rates, deltas, ids and hashes appear below.

**DESCRIPTIVE.** This note gives the numbers and says which side of the pre-declared rule they fall on. The
verdict word belongs to the coordinator (decision 139). These are development numbers on a TRAIN construction
fold (decisions 28 and 86). They are branch-local, never a system-level or test claim. The claim ceiling is
"nominated".

## 1. What flew

Driver step 2 of `SAEA-Queue-NEXT`'s P-SV chain (`scripts/flights/psv/batch_chain_psv.sh psv2 psv3`) at flight
commit `c6e98e6b`, clean tree (`study_repo_dirt` empty). The smoke passed inspect at 23:25:29Z (never scored). The
arm ran 23:25:39Z to 01:58:46Z (rc 0, 2 h 33 min wall). Arm-inspect PASS (attempt FINALIZED, manifest COMPLETED, one
score job) and step-done came at 01:58:55Z. The queue logged `NEXT DONE` at 01:59:15Z.

| run | rows | contacts | speech s | prompt / completion tokens | GPU-h | state |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `SAEA-SLURP-STAGE3-PSV3-FOLD-B-V1` | 1,080 | 8,707 | 25,436.679 | 68,259,780 / 559,787 | not recorded; wall 2 h 33 min | COMPLETED, FINALIZED, scored once |

Dispositions: finite completion 5, revision limit 1. Tool calls 0. Run manifest sha256
`2070d42e9bf7fc969fc8cf5ce0af92be39d18a3739b7a318dd48fd43dc9bada7`, outputs
`1f23a293e5e2b288cb97d85efac65964332d91009d59bc65be35fd185e8201b2`, scores
`31436eb4c1fa5529647b080a001cea40e938ed106df8ca0d24d8cb64939791d2`.

The two non-delivering Perception branches add 4 contacts per row, 4,320 in total, which is 49.6 % of the
flight's 8,707.

**Supply and fit (the branch's declared change).** Boundary items supplied per Perception contact:

| branch | 12 items | 11 | 8 | 3 / 1 / 0 | prompt tokens per Perception contact, mean / max |
| --- | ---: | ---: | ---: | --- | --- |
| `a-agree` (delivering) | -- | -- | 1,076 | 1 / 1 / 2 | 3,594.9 / 3,814 |
| `b-depth` (top_l 12) | 1,073 | 2 | 1 | 1 / 1 / 2 | 4,138.3 / 4,374 |
| `t-twin` | -- | -- | 1,076 | 1 / 1 / 2 | 3,594.9 / 3,814 |

The depth change was delivered: 12 items on 1,073 rows against 8. It costs +543.4 prompt tokens per Perception
contact, far inside the fit limit (24,576-token slot). The first-visit Solver prompt of each branch column
averages 10,220.7 tokens (max 14,712).

**Custody.** Every row carries a level-2 `saea-perception-branch-arms-v2` receipt (1,080 / 1,080). The delivering
note reproduces the ledger driver's P-node parse on 1,080 / 1,080 rows (0 differ, 0 missing; 20 raw duplicate
rows; collapsed rank never differs from raw rank).

| branch | note_parse_status ok | duplicates-collapsed | list size 1 / 2 / 3 |
| --- | ---: | ---: | --- |
| `a-agree` (delivering) | 1,060 | 20 | 63 / 266 / 751 |
| `b-depth` | 1,055 | 25 | 94 / 241 / 745 |
| `t-twin` | 1,052 | 28 | 46 / 265 / 769 |

The deeper supply makes the note list shorter, not longer: 94 single-candidate notes against 63 (A) and 46 (T).

## 2. Level 1: the branch note (primary: gold-on-list)

| branch | top1 % | present % | rank 1 | rank 2 | rank 3 | absent | mean gold rank when present |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `a-agree` | 81.57 | 91.67 | 881 | 86 | 23 | 90 | 1.133 |
| `b-depth` | 80.83 | 90.28 | 873 | 82 | 20 | **105** | 1.125 |
| `t-twin` | 81.57 | 91.20 | 881 | 84 | 20 | 95 | 1.126 |

| contrast (right minus `a-agree`) | metric | delta pp | CI95 pp | half-width | discordant |
| --- | --- | ---: | --- | ---: | ---: |
| twin null `t-twin` | present | -0.46 | [-1.02, +0.09] | 0.56 | 9 |
| twin null `t-twin` | top1 | 0.00 | [-0.74, +0.74] | 0.74 | 16 |
| `b-depth` (primary) | present | **-1.39** | **[-2.31, -0.56]** | 0.88 | 23 |
| `b-depth` | top1 | -0.74 | [-1.85, +0.37] | 1.11 | 40 |

The twin present bar (|offset| + half-width) is 1.0185 pp. The off-list count, which this branch was built to
move, goes the wrong way: absent rises from 90 to 105 (+15 net rows). On this flight the presence ceiling is A's
90 absent rows, 8.33 pp. The CI95 lies wholly below zero. Widening the boundary supply from 8 to 12 items
**lowers** gold-on-list on the Perception note.

## 3. Level 2 beside (never gating): the branch Solver column (official, `slurp-slu-official-train`)

| column | intent % | official SLU-F1 % | per-row SLU-F1 % |
| --- | ---: | ---: | ---: |
| `a-agree` (delivering) | 82.96 | 61.78 | 43.06 |
| `b-depth` | 82.96 | 61.79 | 43.01 |
| `t-twin` | 82.96 | 62.21 | 43.19 |

| contrast (right minus `a-agree`) | metric | delta pp | CI95 pp | half-width | saves / harms |
| --- | --- | ---: | --- | ---: | --- |
| twin null `t-twin` | intent | 0.00 | [-0.28, +0.28] | 0.28 | 1 / 1 |
| twin null `t-twin` | official SLU-F1 | +0.43 | [-0.11, +1.01] | 0.56 | -- |
| twin null `t-twin` | per-row SLU-F1 | +0.13 | [-0.21, +0.46] | 0.33 | 12 / 9 |
| `b-depth` | intent | 0.00 | [-0.28, +0.28] | 0.28 | 1 / 1 |
| `b-depth` | official SLU-F1 | +0.01 | [-0.42, +0.44] | 0.43 | -- |
| `b-depth` | per-row SLU-F1 | -0.05 | [-0.33, +0.23] | 0.28 | 7 / 9 |

The level-2 intent column does not move (1 save / 1 harm). The Solver absorbs the presence loss downstream: when
gold is absent from the `b-depth` note, the Solver still answers it on 9 of 105 rows.

Conversion P(correct intent at level 2 | gold rank r in the branch note), against the ledger's 97.57 / 26.98 /
12.0 %:

| branch | rank 1 | rank 2 | rank 3 | absent |
| --- | --- | --- | --- | --- |
| `a-agree` | 98.52 % (868 / 881) | 29.07 % (25 / 86) | 8.70 % (2 / 23) | 1.11 % (1 / 90) |
| `b-depth` | 97.71 % (853 / 873) | 35.37 % (29 / 82) | 25.00 % (5 / 20) | 8.57 % (9 / 105) |
| `t-twin` | 98.30 % (866 / 881) | 27.38 % (23 / 84) | 15.00 % (3 / 20) | 4.21 % (4 / 95) |

## 4. The registered rule, applied mechanically

NOMINATED (as a presence change) iff the present CI95 lower bound is above zero AND the point delta exceeds the
twin's present bar.

- present CI95 lower bound above zero: -2.31, **no**;
- present point exceeds the twin present bar 1.02: -1.39, **no**.

The numbers fall in the **NOT NOMINATED** branch (driver verdict `NOT NOMINATED`). The point is also a loss larger
than the twin bar (|-1.39| > 1.02), and the CI95 excludes zero.

## Verdict (read agent, for the coordinator)

NOT NOMINATED by the registered presence rule. Deepening the Perception boundary supply from 8 to 12 items
(delivered on 1,073 rows, +543 prompt tokens per Perception contact) moves gold **off** the list: -1.39 pp
[-2.31, -0.56], absent 90 -> 105. The loss exceeds the twin's 1.02 pp bar, and the notes grow shorter (94
single-candidate notes against 63). The level-2 intent and SLU-F1 columns are flat (0.00 [-0.28, +0.28];
+0.01 [-0.42, +0.44]). Across the three P-SV branches, no change to the Perception note (presentation, list
length or supply depth) has moved gold-on-list upward beyond its twin. The coordinator's verdict clause is
pending.

## Coordinator verdict (Fable 5.1, 2026-09-30)

- **P-SV-3 boundary depth 8 -> 12: NOT NOMINATED, branch-local harm on presence; the boundary-depth line is closed.** Gold-on-list -1.39 [-2.31, -0.56] against the twin bar 1.02 (absent 90 -> 105; single-candidate notes 63 -> 94; +543 prompt tokens per Perception contact); level-2 intent 0.00 [-0.28, +0.28], SLU-F1 +0.01. Showing Perception more boundary evidence shortens its list and drops gold. Development number (decisions 28/86).
- **Perception-side conclusion (P-SV-1, P-SV-2, P-SV-3).** No change to the Perception note -- contrast presentation, forced list length, or supply depth -- moved gold-on-list upward beyond its twin; two of three moved it down. The consumption thesis at the Perception node is therefore closed in its presentation forms: the module's Perception component list stays AGREE (agreement-weighted supply ranking) + the centroid boundary key, both retrieval-side. The remaining intent levers are (i) recall for the 34 off-block rows through the retrieval key, (ii) the 49 in-block-not-in-note rows through a shorter, better-ranked block rather than a longer one (an ablation of depth 8 -> 6 or 5 is the honest next probe, offline first from the sealed ranks), and (iii) the Solver-side contrast action (P-SV-1's rank-2 conversion 41.5 % vs 19.5 %), read as a module column at the Solver node. Same-flight instrument: present null 0.46-0.56, intent null 0.00-0.09 across the three flights.
- **Amendment (2026-09-30, same source).** Lever (ii), a shorter block, is closed in both directions: the depth effect is displacement (depth-12 notes spent 45 candidate slots on ranks 9-12 and recovered gold on none of the 7 rows there; P(note keeps gold | in block) 96.45 % at depth 8, 94.32 % at depth 12), and a depth-6 block predicts at best about +4 presence rows (+0.4 pp, under the twin bar) while losing gold from the block on 10-12 rows per pool; a variable-depth (score-cut) block loses to a fixed block of the same size under cross-fit. Lever (iii) is struck (see the P-SV-1 amendment). Lever (i), off-block recall: among the pinned keys only centroid + agreement (COMP-1b's key) is net positive on both folds (+8 / +12 rows) and it brings only 8 of the 34 off-block rows into the top 8 (19 of them sit at ranks 21-60; `general_quirky` leads the misses); further recall needs a NEW, unpinned retrieval key under its own brief. The module's Perception boundary key is confirmed as centroid + agreement (the P-SV cells flew the description key).
