# SLURP node information-gain ledger (TRAIN Fold A)

Date: 2026-09-28. Read id `SLURP-NODE-GAIN-LEDGER-FOLD-A-V1`, recipe `slurp-node-information-gain-ledger-v1`. **Status: DESCRIPTIVE.** This is a model-free read over sealed bytes on TRAIN Fold A (1,080 rows, a construction roster). It made zero model, server, tokenizer, encoder, embedder, network, GPU and paid-API contacts and ran no official-scorer subprocess. It registers no cell, admits nothing, authorises no flight and makes no effectiveness, superiority or generalisation claim. Every number is a development number (owner decisions 28 and 86).

The owner's principle (2026-09-28) is that every node must produce an effective information gain, and a node that does not is redesigned or supplemented. Intent and slots are treated separately. This note measures the state of the gold answer after every node of the flown program, and the gain or loss each node adds.

Driver: `scripts/analysis/slurp_node_gain_ledger.py`. Machine outputs are in `$SPEECHRL_DATA_DIR/analysis/SLURP-NODE-GAIN-LEDGER-FOLD-A-V1/`: `report.json`, `ledger.md` and `content-sha256.json`. Every table below is quoted from `ledger.md`. One row is 0.0926 pp.

## 0. Systems, nodes and what each node receives

| arm | run id | phases sha256 | outputs sha256 | scores sha256 | official intent acc |
| --- | --- | --- | --- | --- | ---: |
| AGREE (primary) | `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` | `783299f15626` | `6a4256e09278` | `01db05fa5778` | 85.83 |
| wave A/A (replicate: the same bytes re-flown) | `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` | `37425ffc066e` | `548ba6662b31` | `e935745a2cc4` | 85.65 |

Both arms fly program `phase-native-candidates-review-revise-v1` (`configs/policy/phase-native-candidates-review-revise-v1.json`: perception, reviewer, planner, solver; `max_contacts` 11). The sealed agent-state order is Perception, Solver, Reviewer, Planner on 1,053 AGREE rows. On 23 rows it is followed by a second Solver, Reviewer and Planner after a REVISE route. On 4 rows it stops at Perception and Solver. The wave A/A counts are 1,037, 29 and 14. The nodes, in flight order, are:

| code | node | sealed channel | what it receives (trace, AGREE; wave A/A identical in kind) |
| --- | --- | --- | --- |
| B | boundary block (retrieval) | `initial_query_state.retrieved_value_ids` (8 intent-boundary entries) | retrieved **before** Perception |
| P | Perception | `agent_states` `phase:perception` (`slurp-intent-hypotheses-v1`: 1-3 candidates with `intent_id`, `distinction`, `evidence_refs`, `unresolved_fields`) | audio (speech feature parts on 1080/1080 contacts) plus the 8 boundary entries only (1080/1080; order equals the block on 1080/1080) |
| K | knowledge wave 0 | `waves[0].fusion_decision` (20 annotated train exemplars plus the slot-contract cards) | acquired after Perception and supplied to Solver, Reviewer and Planner |
| S1 | Solver, first answer | first `phase:solver` state | audio (1103/1103 Solver contacts), the Perception note in history (1103/1103), boundaries plus exemplars plus cards (first-Solver order equals the sealed supply on 1080/1080) |
| R | Reviewer / Planner | `phase:reviewer` (free text), `phase:planner` and the `planner_routes` receipt; S2 = the last Solver state | audio, the history and the same supply |
| D | delivery | sealed `outputs.jsonl` (after the deliver normaliser; this is what the scorer read) | the final Solver text; `final_response_text` differs from the last Solver state on exactly the 108 normaliser-changed rows |

**The Solver receives the audio, not only the Perception note.** Every Solver request carries speech feature parts (`mmproj_loaded` false: the precomputed-feature path) and the Perception note in its history. The Perception note carries no scores: `evidence_refs` and `unresolved_fields` are empty on every candidate. The only uncertainty proxy is therefore log2 of the candidate-set size. The note is an intent-hypothesis note, not a transcript. It carries no slot spans and no slot types.

Structural checks (both arms): parse, intent and in-process SLU counts agree with the sealed scores on 1080/1080 rows. This is the error-source read's `structural_checks`, imported unchanged. All 20 rendered exemplar keys resolve in the pinned M1 snapshot on every row. The row's own utterance is rendered as an exemplar on 0 rows.

## 1. Intent ledger

### 1.1 Node states

"Top-1" means the gold intent is the node's leading choice: block position 1, Perception rank 1, the exemplar-vote winner, or the answer. "Present" means gold is in the node's set: in the block, on the shortlist, among the exemplars, or answered.

| node | agree gold top-1 | agree gold present | wave A/A gold top-1 | wave A/A gold present | agree mean log2 set size (bits) | top-1 rate agree minus wave A/A pp [95 % CI] |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B boundary block (before Perception) | 831 | 1040 | 831 | 1040 | 2.995 | +0.00 [+0.00, +0.00] |
| P Perception note | 907 | 995 | 904 | 997 | 1.406 | +0.28 [-0.56, +1.20] |
| K exemplar supply (20, vote) | 832 | 1033 | 832 | 1033 | 1.117 | +0.00 [+0.00, +0.00] |
| S1 Solver first answer | 907 | 907 | 907 | 907 | 0.0 | +0.00 [-1.02, +1.02] |
| R after Reviewer/Planner | 906 | 906 | 908 | 908 | 0.0 | -0.19 [-1.30, +0.93] |
| D delivered (sealed, scored) | 927 | 927 | 925 | 925 | 0.0 | +0.19 [-0.74, +1.11] |

For K the bits column is the mean entropy of the exemplar intent votes: 3.75 distinct intents on average, and a mean gold surprisal of 0.869 bits where gold is present. Perception list sizes on AGREE are 1: 35, 2: 235, 3: 810 (mean 2.72). Retrieval (B, K) is deterministic, so the two flights are identical there.

### 1.2 Decision-edge gains

| edge | arm | improves | worsens | stays right | stays wrong | net | net pp [95 % CI] | presence lost | presence gained | P(top-1 at b given present at a) % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| B->P | agree | 105 | 29 | 802 | 144 | 76 | +7.04 [+5.00, +9.07] | 50 | 5 | 86.83 |
| B->P | wave_aa | 99 | 26 | 805 | 150 | 73 | +6.76 [+4.81, +8.70] | 48 | 5 | 86.54 |
| P->S1 | agree | 22 | 22 | 885 | 151 | 0 | +0.00 [-1.20, +1.20] | 90 | 2 | 90.95 |
| P->S1 | wave_aa | 21 | 18 | 886 | 155 | 3 | +0.28 [-0.83, +1.39] | 91 | 1 | 90.87 |
| S1->R | agree | 2 | 3 | 904 | 171 | -1 | -0.09 [-0.56, +0.28] | 3 | 2 | 99.67 |
| S1->R | wave_aa | 3 | 2 | 905 | 170 | 1 | +0.09 [-0.28, +0.46] | 2 | 3 | 99.78 |
| R->D | agree | 21 | 0 | 906 | 153 | 21 | +1.94 [+1.20, +2.78] | 0 | 21 | 100.0 |
| R->D | wave_aa | 17 | 0 | 908 | 155 | 17 | +1.57 [+0.83, +2.41] | 0 | 17 | 100.0 |

Row-level stability (the same row shows the event in both flights):

| edge | improves agree | improves wave A/A | improves in both | worsens agree | worsens wave A/A | worsens in both |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B->P | 105 | 99 | 95 | 29 | 26 | 23 |
| P->S1 | 22 | 21 | 14 | 22 | 18 | 11 |
| S1->R | 2 | 3 | 0 | 3 | 2 | 1 |
| R->D | 21 | 17 | 12 | 0 | 0 | 0 |

Two gains are stable and resolved: Perception's re-ranking of the block (net +76 / +73 rows, CI clear of zero in both flights) and the deliver normaliser's label repair (+21 / +17). The normaliser changed 108 rows, 32 of them in the label. The Solver's net intent gain over Perception is 0 and +3 rows. Its CIs straddle zero, and fewer than two thirds of its individual flips recur in the replicate. The Reviewer/Planner node moves 5 rows in each flight with a net of -1 and +1.

### 1.3 Conversions (AGREE; wave A/A in `ledger.md`)

| gold block position | rows | Perception lists gold | Perception rank 1 | Solver first correct | delivered correct |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 831 | 828 | 802 | 804 | 813 |
| 2-3 | 160 | 140 | 88 | 85 | 96 |
| 4-8 | 49 | 22 | 13 | 12 | 12 |
| absent | 40 | 5 | 4 | 6 | 6 |

| gold Perception rank | rows | gold in block | Solver first correct | Solver answer on the list | delivered correct | P(Solver correct) % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 907 | 903 | 885 | 889 | 899 | 97.57 |
| 2 | 63 | 63 | 17 | 58 | 21 | 26.98 |
| 3+ | 25 | 24 | 3 | 21 | 5 | 12.0 |
| absent | 85 | 50 | 2 | 76 | 2 | 2.35 |

| Perception list / exemplar vote | rows | Solver first correct | % |
| --- | ---: | ---: | ---: |
| off list / 0 votes | 36 | 0 | 0.0 |
| off list / outvoted | 46 | 2 | 4.35 |
| off list / top vote | 3 | 0 | 0.0 |
| on list / 0 votes | 11 | 9 | 81.82 |
| on list / outvoted | 155 | 95 | 61.29 |
| on list / top vote | 829 | 801 | 96.62 |

Reviewer / Planner (AGREE): the Reviewer visited 1,076 rows. The Planner routed REVISE on 23 rows: 14 with a right first answer and 9 with a wrong one. It accepted 162 wrong first answers. Of the 23 revisions, 10 changed the intent and 8 changed the entities; 2 moved to gold and 3 moved away from it. The wave A/A figures are 29 revisions, 3 moved to gold and 2 away, and 157 wrong first answers accepted. The Solver's answer is on Perception's list on 1,044 of 1,080 rows.

### 1.4 Top-2 sizing on delivered-wrong rows

| quantity | agree | wave A/A |
| --- | ---: | ---: |
| intent-wrong rows | 153 | 155 |
| gold at Perception rank 1 | 8 | 5 |
| gold at Perception rank 2 | 42 (list of 2: 11, list of 3: 31) | 50 (13, 37) |
| gold at Perception rank 3 | 20 | 19 |
| gold absent from the Perception list | 83 | 81 |
| of which gold in the boundary block | 49 | 48 |
| of which gold outside the block | 34 | 33 |
| gold is the catch-all `general_quirky` | 29 | 29 |
| unparsed | 1 | 0 |

## 2. Slot ledger (941 gold entity items)

Item classes are the error-source read's (`entity_items`, imported unchanged). They are applied at S1, at R (the last Solver state) and at D (the delivered text). EXACT means an exact {type, filler} match. SPURIOUS counts predictions that have no gold item.

### 2.1 Node states

| node | arm | EXACT | FORMAT | BOUNDARY | NEAR | WRONG-VALUE | WRONG-TYPE | MISSING | SPURIOUS | SLU-F1 micro |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 Solver first | agree | 502 | 43 | 75 | 56 | 41 | 51 | 173 | 255 | 63.89 |
| S1 Solver first | wave_aa | 501 | 36 | 76 | 56 | 42 | 54 | 176 | 266 | 63.12 |
| R after Reviewer/Planner | agree | 502 | 43 | 75 | 56 | 41 | 51 | 173 | 253 | 63.94 |
| R after Reviewer/Planner | wave_aa | 503 | 36 | 76 | 55 | 42 | 54 | 175 | 269 | 63.11 |
| D delivered | agree | 534 | 11 | 75 | 56 | 41 | 51 | 173 | 253 | 65.16 |
| D delivered | wave_aa | 529 | 11 | 76 | 54 | 42 | 54 | 175 | 269 | 64.16 |

| SLU-F1 node gain | pp [95 % CI] |
| --- | ---: |
| agree S1 -> R | +0.05 [-0.13, +0.21] |
| agree R -> D | +1.22 [+0.80, +1.66] |
| wave A/A S1 -> R | -0.01 [-0.29, +0.33] |
| wave A/A R -> D | +1.04 [+0.65, +1.45] |
| D, agree minus wave A/A | +1.00 [-0.31, +2.29] |

Per-edge item movement (AGREE). At S1 -> R, 1 MISSING item was repaired, 1 EXACT item was broken, and 2 items changed kind. The other 937 items did not move. At R -> D, the normaliser repaired 35 of 43 FORMAT items and broke 3 EXACT items. BOUNDARY, NEAR, WRONG-VALUE, WRONG-TYPE and MISSING did not move at either edge. The wave A/A figures are S1 -> R: 3 repaired, 1 broken; R -> D: 28 FORMAT and 1 NEAR repaired, 3 broken.

### 2.2 Upstream states: the Perception note and the delivered knowledge

The Perception note state is computed per gold item on the canonical form (the error-source read's `canonical`) of the note's `distinction` and `unresolved_fields` text:

- CONTIGUOUS: the gold token span appears contiguously in the note.
- NEAR: a window of the gold length ±1 tokens lies within canonical distance 0.4.
- PARTIAL: a non-function gold token appears in the note.
- ABSENT: none of the above.

| Perception note state (AGREE) | gold items | S1 exact | D exact | D kinds |
| --- | ---: | ---: | ---: | --- |
| CONTIGUOUS | 364 | 243 | 261 | BOUNDARY 29, FORMAT 2, MISSING 44, NEAR 4, WRONG-TYPE 20, WRONG-VALUE 4 |
| NEAR | 96 | 41 | 40 | BOUNDARY 9, FORMAT 1, MISSING 14, NEAR 20, WRONG-TYPE 7, WRONG-VALUE 5 |
| PARTIAL | 26 | 9 | 10 | BOUNDARY 5, MISSING 1, NEAR 4, WRONG-TYPE 4, WRONG-VALUE 2 |
| ABSENT | 455 | 209 | 223 | BOUNDARY 32, FORMAT 8, MISSING 114, NEAR 28, WRONG-TYPE 20, WRONG-VALUE 30 |

Knowledge uses the W5 estimate's method: `printed_pairs` over the pinned M1 snapshot, restricted to the row's 20 rendered exemplars.

| delivered knowledge (AGREE) | gold items | type card delivered | S1 exact | D exact |
| --- | ---: | ---: | ---: | ---: |
| gold value printed (type + value) | 543 | 541 | 372 | 380 |
| value printed under another type only | 6 | 6 | 1 | 1 |
| value not printed | 392 | 381 | 129 | 153 |

The note state is the same in both flights on 796 of 941 items. The type card was delivered for 928 of 941 gold items.

### 2.3 Origin split of the delivered errors

Precedence: (1) right at S1 and wrong at D means **introduced after the Solver**; otherwise, for an item already wrong at S1, the note decides. (2) The gold span is CONTIGUOUS in the note means **consumption origin**: the upstream note carried it and the Solver still missed it. (3) The note carries a NEAR or PARTIAL form means **hearing/span origin (visible)**. (4) The note is silent means **undetermined**. The note is an intent note, so its silence is not evidence of mis-hearing.

| origin (delivered gold-side errors) | AGREE | wave A/A |
| --- | ---: | ---: |
| all delivered gold-side errors | 407 | 412 |
| consumption: note carries the gold span, Solver first answer wrong | 103 | 116 |
| consumption: introduced after the Solver (Reviewer revision 1, normaliser 3) | 4 | 4 |
| **consumption origin, total** | **107** | **120** |
| of which gold value printed in the delivered exemplars | 55 | 61 |
| hearing/span origin, visible: note carries a near form | 55 | 49 |
| hearing/span origin, visible: note carries a partial form | 16 | 12 |
| **hearing/span origin, total visible** | **71** | **61** |
| undetermined: note silent | 229 | 231 |
| SPURIOUS predictions at D (not in the split) | 253 | 269 |
| of which the predicted filler is contiguous in the note | 74 | 77 |

AGREE kinds by origin: consumption at the Solver is BOUNDARY 29, FORMAT 2, MISSING 44, NEAR 4, WRONG-TYPE 20, WRONG-VALUE 4. Visible hearing/span (near plus partial) is BOUNDARY 14, MISSING 15, NEAR 24, WRONG-TYPE 11, WRONG-VALUE 7. Undetermined is BOUNDARY 32, FORMAT 6, MISSING 113, NEAR 28, WRONG-TYPE 20, WRONG-VALUE 30. The base rate is that 261 of the 534 delivered-exact items (48.9 %) are contiguous in the note, against 103 of the 407 errors (25.3 %). Of AGREE's 407 delivered errors, 376 are also errors in the replicate, 341 of them with the same kind.

### 2.4 Re-listen addressability

Delivered BOUNDARY, NEAR and FORMAT items number 142 on AGREE (75 + 56 + 11). **35 have the gold span contiguous in the Perception note: BOUNDARY 29, NEAR 4, FORMAT 2. The other 107 do not:** 30 have a near form in the note, 9 a partial form and 68 are absent from it. The wave A/A figures are 141 items: 40 contiguous and 101 not (22 near, 7 partial, 72 absent).

## 3. What this says about the three consumption routes (numbers only)

- **Discriminative presentation at the decision node.**
  - The Solver's net intent gain over Perception is 0 rows (+0.00 [-1.20, +1.20]); on the replicate it is +3 (+0.28 [-0.83, +1.39]).
  - The Solver's answer is on Perception's list on 1,044 of 1,080 rows.
  - Gold at Perception rank 1 converts at 97.57 %, rank 2 at 26.98 % (17 of 63) and rank 3 at 12.0 %.
  - Of the 153 wrong rows, gold is at Perception rank 2 on 42 (3.89 pp; 50 on the replicate), at rank 3 on 20 and at rank 1 on 8.
  - Gold on the list but outvoted in the exemplars converts at 61.29 % (95 of 155 rows).
  - The Reviewer/Planner node moves 5 rows (net -1). It accepted 162 wrong first answers and revised 9.
- **Progressive loading of closed vocabularies.**
  - Intent. The block carries 2.995 bits and Perception reduces it to 1.406 bits, gaining a net +76 top-1 rows and losing presence on 50 rows. Gold is off the list but in the block on 49 of the wrong rows and outside the block on 34. Gold off the list converts at 2.35 %.
  - Slots. The type card was delivered for 928 of 941 gold items. The gold value was printed in the exemplars for 543 items (S1 exact 68.5 %) and not printed for 392 (32.9 %). The 173 MISSING items and 51 WRONG-TYPE items do not move after S1.
- **Targeted re-listen.**
  - 35 of 142 delivered BOUNDARY + NEAR + FORMAT items have the gold span contiguous in the Perception note; 107 do not.
  - Visible hearing/span-origin errors number 71 of 407, against 107 of consumption origin and 229 undetermined.
  - The Reviewer/Planner round, which already carries the audio, repaired 1 slot item and broke 1.

## 4. Method, files read, reproduce

Every file read (paths relative to `$SPEECHRL_DATA_DIR`; full SHA-256 values are in `report.json`):

- per arm: `runs/<run>/<attempt>/<run>.phases.json`, `.outputs.jsonl`, `.scores.json` and `.trace.jsonl`. The trace was streamed once and only ids, roles and counts were kept;
- gold: the governed TRAIN split through `ES.load_gold`, which is `data.slurp.load_slurp_split`, the error-source read's own path;
- the exemplar pool `knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json` (`fcb5506c6365`), read both through `GP.load_exemplar_pool` and through W5's `snapshot_values` with its content-hash pin `4c498dc02820`;
- `datasets.lock.json` (umbrella).

Reused code (imported unchanged; hashes in `report.json`):

- `scripts/analysis/slurp_agree_arm_error_sources.py`: gold, outputs, scores, `entity_items`, `canonical`, `slu_counts`, `structural_checks`;
- `scripts/analysis/slurp_gold_position_and_solver_freedom_read.py`: `load_phases` and `load_exemplar_pool`; the trace pass mirrors its `verify_trace`;
- `scripts/analysis/slurp_w5_fold_a_offline_estimate.py`: `printed_pairs` and `snapshot_values`.

The CIs are 95 % percentile intervals from the programme's paired row bootstrap (`analysis.bootstrap.paired_cluster_bootstrap`, seed 20260807, 10,000 replicates). No utterance text, transcript, filler, gold label value, Perception note or model output is printed or persisted.

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/slurp_node_gain_ledger.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
# byte check against the written outputs (everything except generated_at):
PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/slurp_node_gain_ledger.py --check --data-root "$SPEECHRL_DATA_DIR"
```

Content hashes of the outputs with `generated_at` removed: `report.json` 84d43d854f8bab6a5f693fe1507684344f910ba88f01d31234a743c3b7ea2283 and `ledger.md` 995b87c1f5e1a87a2dab444eb206d4119f8cdf885fe40490f8a0beb22ea69284. A `--check` re-run reported IDENTICAL apart from `generated_at`.

Limits:

- The Perception note-state classes are a textual proxy. NEAR can fire on short tokens.
- The Reviewer's verdict is free text, so ACCEPT and REVISE are read from the Planner route receipt.
- Rows without a Reviewer visit (4 AGREE, 14 wave A/A) enter R with their S1 state.

## 5. Coordinator reading (Fable 5.1, 2026-09-28)

Recorded by Claude Opus 5.5 at the coordinator's direction. Every number below is quoted from sections 1-3 of this note, except the E3 omission count, which is quoted from the E3 spec. This reading registers no cell and authorises no flight.

1. **Intent: the deciding node is Perception's shortlist and its order.**
   - Perception gains +7.04 [+5.00, +9.07] pp over the boundary block. The Solver adds 0.00 [-1.20, +1.20]. The Reviewer/Planner node nets -1 row. The deliver normaliser adds +1.94 [+1.20, +2.78].
   - Conversion by Perception rank is 97.6 % (rank 1), 27.0 % (rank 2) and 12.0 % (rank 3).
   - Of the 153 wrong rows, gold is at Perception rank 2 on 42 (3.89 pp), at rank 3 on 20, and off the list on 83 (49 of them still in the boundary block, 34 outside it).
   - Consequence: the contrast action (owner decisions 178 and 180) must reach Perception's shortlist or its ranking, or give the Solver a warranted reason to leave rank 1. The RANKVIS probe (Solver-side) stays queued as a cheap test, but its effect is expected to be bounded by the rank-2 and rank-3 conversion rates. Phase 2 of the same-flight instrument (`docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-design.md`, the Q1 ruling: Perception-phase variants as an episode-level fork with their own A/A) is now the priority engineering item.
2. **Slots: no error class moves after the Solver's first answer, except FORMAT through the normaliser** (+1.22 [+0.80, +1.66] pp SLU-F1).
   - Of the 407 delivered gold-side errors, 107 are of consumption origin (103 with the gold span contiguous in the Perception note; 55 with the gold value printed in the delivered exemplars), 71 are visible hearing/span origin, and 229 are undetermined, because the note is not a transcript.
   - Re-listen-addressable BOUNDARY + NEAR + FORMAT items: 35 of 142. SPURIOUS predictions: 253, of which 74 have the predicted filler in the note.
   - Consequence for E4 v1 (`docs/superpowers/specs/2026-09-28-e4-core-native-targeted-relisten-design.md`): it gains a second shadow column, "replace + drop-when-unheard", aimed at the 253 SPURIOUS items. The blind re-listen also yields the hearing state of the 229 undetermined items, which is a diagnostic gain in itself.
   - E3 (type-first, `docs/superpowers/specs/2026-09-28-e3-progressive-slot-loading-design.md`) is supported by 34 of the 41 closed-type misses being omissions at the Solver (E3 spec, Q1). It flies after E4, as a cross-flight no-harm enabler.
3. **E6: this ledger is the first instance of the information-gain gate.** Nodes with no measurable gain today are the Solver (intent) and the Reviewer/Planner (intent and slots). Under the owner's principle each is to be redesigned or supplemented.
