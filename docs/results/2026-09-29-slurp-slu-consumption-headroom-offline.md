# SLURP SLU consumption headroom on the AGREE arm: no SLU mechanism reaches 1.5 pp at a measured conversion (DESCRIPTIVE, offline)

Date: 2026-09-29. Read id `SAEA-SLURP-SLU-CONSUMPTION-HEADROOM-OFFLINE-V1`, recipe
`slurp-slu-consumption-headroom-offline-v1`, written by Claude Opus 5.5 for the coordinator in worktree
`fable/w5offline` (base master `109538e87`). The brief is owner decision 192 (2026-09-29): before any SLU mechanism is
registered, a model-free information-gain analysis must predict at least **1.5 pp** official SLU-F1. That bar is the
measured same-flight SLU contrast half-width at n = 1,080 (1.48656 pp,
`docs/results/2026-09-29-slurp-same-flight-floor-recalibration.md:81`; 1.49 proposed for decision 190,
`docs/results/2026-09-29-slurp-w4sv-fold-a-column-read.md:313`). Below it, a mechanism goes cross-flight on
DEV-2000-ADDED (bar 2.5 pp) or nowhere.

**Status: DESCRIPTIVE.** Development numbers on TRAIN Fold A, a construction roster (owner decisions 28 and 86). The
read made zero model, server, tokenizer, encoder, embedder, GPU, network and paid-API contacts and ran no
official-scorer subprocess. Counterfactuals use the official arithmetic in-process. It registers no cell, admits
nothing and authorises no flight. Gold entered only offline, through the governed TRAIN loader
`data.slurp.load_slurp_split` (the loader `ES.load_gold` wraps). No utterance text, transcript, gold value, filler,
card body or model output is printed or persisted: only counts, rates, pp, slot TYPE names, ids and hashes.

**What this note does not claim.** It does not claim that any mechanism works or fails in flight. Every "expected"
figure multiplies an exact oracle by a conversion measured elsewhere, which is an analogue and not a measurement of the
mechanism itself. No test-split, generalisation or superiority claim is made.

Driver: `scripts/analysis/slurp_slu_consumption_headroom.py` (unit test
`tests/unit/test_slurp_slu_consumption_headroom.py`, 16 fakes). Machine outputs:
`$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-SLU-CONSUMPTION-HEADROOM-OFFLINE-V1/` (`report.json`, `tables.md`,
`content-sha256.json`). Every new number below is quoted from `tables.md`, section named in brackets. The driver
imports and reuses:

- the node ledger's `derive_arm` and `slot_ledger`, unchanged. Its published counts are asserted on every run:
  407 / 107 / 103 / 55 / 71 / 229 / 253 / 74 / 35 / 142 (`docs/results/2026-09-28-slurp-node-information-gain-ledger.md:170-186`);
- the error-source read's `repaired` and `slu_counts`;
- W5's `printed_pairs` and `snapshot_values` (the W5 newly-shown count of 10 is asserted);
- `analysis.sealed_credit.entity_states.entity_items` and `canonical`;
- `analysis.sealed_credit.row_states.load_scores` for the sealed totals;
- the programme bootstrap (`paired_cluster_bootstrap` through the ledger's `boot_f1`, seed 20260807, 10,000 draws).

## 1. Item counts to SLU-F1 pp

Official pooled SLU-F1 is the F1 of the word-distance plus char-distance TP/FP/FN totals
(`src/speech_aware_evidence_acquisition/reproduction/slurp_scoring.py:271-279`). The sealed AGREE totals
(`SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1`, scorer `slurp-slu-official-train`) are **TP 1,434.0, FP 846.821, FN 686.821**,
which gives SLU-F1 **65.1575** [Sealed totals]. The in-process totals reproduce them to 1e-6.

A wholly spurious prediction adds 1.0 FP to each channel, and a wholly missed gold item adds 1.0 FN to each channel.
Removing k false positives therefore moves FP by -2k. Recovering k missed items exactly moves TP by +2k and FN by -2k.
A missed item is worth about twice a false positive, because it adds to the numerator as well.

| k (converted items) | remove k FP, pp | recover k FN, pp | both (k of each), pp |
| ---: | ---: | ---: | ---: |
| 10 | 0.297 | 0.610 | 0.909 |
| 20 | 0.598 | 1.214 | 1.818 |
| 35 | 1.053 | 2.111 | 3.181 |
| 50 | 1.515 | 2.995 | 4.544 |
| 74 | 2.267 | 4.386 | 6.725 |
| 107 | 3.330 | 6.252 | 9.724 |
| 142 | 4.494 | 8.173 | 12.904 |
| 173 | 5.559 | 9.827 | 15.721 |
| 253 | 8.463 | 13.903 | 22.991 |

[Conversion table]. Cross-check against an exact re-score of the whole class [Whole-class cross-check]:

- all 173 MISSING: analytic 9.827, exact 9.796 (error-source 9.80, `docs/results/2026-09-27-slurp-agree-arm-error-sources.md:150`);
- all 253 SPURIOUS: analytic 8.463, exact 8.457 (error-source 8.46, `:151`).

Partial-credit kinds (BOUNDARY, NEAR, WRONG-VALUE, FORMAT) are worth less per item. Every mechanism row below
therefore uses the **exact oracle** of its own item set, not the analytic table.

**Minimum items needed to reach the bar** [Minimum items]. The addressable count is `ceil(k* / conversion)`, with
oracle 1.0, CONV probe 0.457 (32 of 70, `docs/results/2026-09-27-slurp-conv-probe-read.md:58-59`) and M1 measured
0.2471 (`docs/results/2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md:51`).

| bar | mode | converted items k* | addressable at oracle 1.0 | at 0.457 | at 0.247 |
| --- | --- | ---: | ---: | ---: | ---: |
| 1.5 pp | remove FP | 49.5 | 50 | 109 | 201 |
| 1.5 pp | recover FN | 24.8 | 25 | 55 | 101 |
| 1.5 pp | both (k of each) | 16.5 | 17 of each | 37 of each | 67 of each |
| 2.5 pp | remove FP | 81.3 | 82 | 178 | 330 |
| 2.5 pp | recover FN | 41.6 | 42 | 91 | 169 |
| 2.5 pp | both (k of each) | 27.5 | 28 of each | 61 of each | 112 of each |

## 2. Mechanism ledger

"Expected" = exact oracle x the named measured conversion. "Unmeasured" means no conversion exists and none is
assumed. Sources for the new numbers are the sections of `tables.md` named in brackets.

| mechanism | addressable items (class, count, source) | conversion (measured rate, origin) | expected pp | oracle pp | harm channel and size | read |
| --- | --- | --- | ---: | ---: | --- | --- |
| **W5 slot exemplars, as built** | 10 newly shown (MISSING 9, BOUNDARY 1; W5 note `:47`, re-derived) [W5] | 0.2471 M1 (W5 note `:51`) | **0.15** (W5 note: 0.14, `:52`) | 0.59 (W5 note isolated-pp form: 0.548) | 9 slot-bearing exemplars on all 414 no-gold rows; SPURIOUS 253 is the largest class (W5 note `:59-60`). VAR-1 analogue 30 vs 20 exemplars: +0.09 [-1.47, +1.60] (`:54`) | same-flight (Solver-supply column) |
| **W5 + value-vocabulary filter** (keep W5 exemplars only for closed / semi-closed types) | 7 of the 10 [W5] | 0.2471 M1 | 0.10 | 0.41 | fewer printed pairs, so less over-tagging exposure. The harm is not measured | same-flight |
| value-vocabulary route in any form (the ceiling of any vocabulary filter) | 79 gold-side error items whose value is in TRAIN's own list for the type and is not printed by M1. All 10 W5 items are among them. Closed types only: 12 items, 0.73 pp. Top-20 values per type: 38 items, 2.28 pp [Vocabulary route; Composition] | list or card form: W4 moved 5 of 97 listed items (K2 omission 85 -> 83, wrong filler 12 -> 9; `docs/results/2026-09-28-slurp-w4-fold-a-read.md:189-190`), rate 0.052 | **0.24** at 0.052. 1.14 at 0.247, but that rate needs exemplars showing the value, and speech-keyed retrieval found 10 of 79 | 4.60 | K3 over-emission of listed values: W4 moved 4 -> 7 (`w4 read :192`). A further 163 error items already have their value printed by M1 and are still wrong (8.98 pp) | same-flight as a supply column |
| **SPURIOUS (i): E4 replace + drop-when-unheard** | 179 SPURIOUS whose filler is not in the Perception note (5.76 pp). The 74 in-note items (2.27 pp) were plausibly heard [Addressable sets] | **unmeasured** (E4-1 reads it; the E4 spec declares 0.0, `docs/superpowers/specs/2026-09-28-e4-core-native-targeted-relisten-design.md` section 8.7) | unmeasured | 5.76 | deleting heard, correct entities: 273 delivered-exact items are not contiguous in the note (534 - 261, ledger `:182`). **Reaching 1.5 alone needs 49.5 net FP removed, which is 0.28 of the 179, net of harm** | same-flight shadow column (`bind()`) |
| **SPURIOUS (ii): B4 explicit empty-entity decision** | 159 FP-only rows (no gold entity, at least 1 prediction) carrying 178 SPURIOUS. Oracle: empty every FP-only row, 5.73 [Explicit empty] | (a) DEV-2000 five-sample vote rule: reaches 14.4 of 162.2 FP-only sample-rows (`docs/results/2026-09-28-slurp-empty-entity-offline-read.md:128-134`) and read +0.256 [+0.067, +0.445] (`:89`). (b) F10, exemplar-delivered empty answers: empty-gold FP 142 -> 120, non-empty FN 384 -> 397 (`docs/results/2026-09-25-slurp-f10-complete-verdict.md:18-21`); pooled +0.34 [-1.42, +2.29] (`docs/results/2026-09-27-slurp-mechanism-synthesis.md:141`) | (a) 0.51 (reach only, harm not netted). (b) **-0.19** net: 27.6 FP removed (+0.83) against 16.3 exact items lost [Explicit empty] | 5.73 | recall loss on gold-bearing rows (F10: +13 FN per 22 FP; DEV-2000 rule: 10.2 gold-bearing edits per mean sample, `empty-entity :131`) | (a) only on multi-sample pools; (b) same-flight supply column |
| **SPURIOUS (iii): do-not-tag scope as row-matched exemplars** | 253 SPURIOUS (183 on intent-right rows, 5.90 pp). **The row's own 20 delivered exemplars already show the predicted phrase untagged for 89 SPURIOUS (2.75 pp), and for 81 of the 534 exact predictions** [SPURIOUS scope] | flown conversion on those 89: 0 (they are still spurious). Rule cards: W4-SV -0.15 [-1.40, +1.11] (`w4sv read :130`). F10 as above | about 0 at the flown form | 2.75 (row-shown) / 8.46 (all) | the same evidence sits beside 81 correct entities, so row-matched untagged exemplars do not separate spurious from correct at this form | same-flight supply column |
| **SPURIOUS (iv): a deterministic deliver-side scope rule** (not in the brief; found by the diagnostic). Drop a delivered entity whose phrase occurs in 5 or more pool exemplars and is untagged in 80 % or more of them | drops 66 predictions: 50 SPURIOUS, 4 exact, 12 partially matched [SPURIOUS scope] | none needed: a deterministic edit whose harm is inside the number. Three thresholds were fixed in code before the first run: 0.5 -> +0.74, **0.8 -> +1.04 [+0.53, +1.57]**, 0.9 -> +0.94. **Wave A/A replicate** at 0.8: +0.93 [+0.46, +1.42] | **1.04** (replicate 0.93) | -- | measured inside: 4 exact and 12 partial matches dropped. The pool is TRAIN minus Fold A (no Fold A utterance, `docs/results/2026-09-27-slurp-knowledge-content-audit.md:35`) | offline on any sealed pool; no flight |
| consumption at the Solver: gold span contiguous in the note | 103 items, 95 rows: MISSING 44 (2.61 pp) plus span/type kinds 59 (BOUNDARY 29, WRONG-TYPE 20, NEAR 4, WRONG-VALUE 4, FORMAT 2; 3.65 pp) [Addressable sets] | **unmeasured** for rank-visible slot spans or a Solver re-read. The closest flown analogue, the Reviewer/Planner round (audio plus history), repaired 1 slot item and broke 1 (ledger `:136`, `:203`) | about 0 at the analogue | 6.29 | a re-read that rewrites entities breaks EXACT items at the same rate it repairs them (1 / 1) | a Solver-visible form needs a second Solver visit, which is cross-flight (E4 spec section 4) |
| consumption with the gold value printed in the exemplars | 55 items (MISSING 29) [Addressable sets] | printing has already been spent: these 55 are the residual after M1's 0.247 | 0 | 3.18 | -- | -- |
| hearing-visible (note near / partial) | 71 items, 69 rows [Addressable sets] | **unmeasured** (E4-1 replace-only column) | unmeasured | 3.47 | E4 replace acceptance, measured by the E4-1 read | same-flight shadow column |
| re-listen addressable (BOUNDARY / NEAR / FORMAT, gold contiguous in the note) | 35 items (BOUNDARY 29) [Addressable sets] | **unmeasured** (E4-1) | unmeasured | 1.55 | as above | same-flight shadow column |
| hearing-visible 71 union re-listen 35 | 106 items, 104 rows [Addressable sets] | **unmeasured** | unmeasured. **Reaching 1.5 alone needs 0.29 of the oracle** | 5.13 | as above | same-flight shadow column |

## 3. The 229 undetermined items: one diagnostic

The Perception note is an intent note, so its silence says nothing about hearing (ledger `:166`). The one model-free
diagnostic is **where, if anywhere, the gold value was present in what the row's Solver was supplied**. The classes
are taken in precedence order:

- E1: the row's 20 exemplars print the gold (type, value);
- E2: the exemplars print the value under another type only;
- E3: a delivered slot-contract card names the value (folded, word-bounded, length at least 3);
- E4: not supplied, but the value is in TRAIN-outside-Fold-A's own value list for the type;
- E5: nowhere but the audio.

Card ids resolved 100 % (0 unresolved). [Evidence split]:

| evidence (undetermined 229) | items | MISSING | not MISSING | exact oracle pp |
| --- | ---: | ---: | ---: | ---: |
| E1 exemplars print the gold (type, value) | 91 | 55 | 36 | 5.12 |
| E2 value printed under another type only | 1 | 0 | 1 | 0.09 |
| E3 a delivered card names the value | 15 | 13 | 2 | 0.99 |
| E4 not supplied; in TRAIN's value list | 40 | 25 | 15 | 2.33 |
| E5 nowhere but the audio | 82 | 20 | 62 | 3.89 |

- **107 of the 229 (E1 + E2 + E3) had the value in the supply and still failed.** That is consumption, not hearing.
  With the ledger's 107 consumption-origin items, consumption-type failure rises to 214 of 407. Across all 407
  delivered errors, 163 are E1: the value was printed by M1 and still missed (8.98 pp).
- **82 items (E5) are audio-only.** 62 of them are not MISSING: the Solver emitted a value for the mention and got
  its span, type or value wrong. These 62 are the natural target of a hearing mechanism, E4-1's blind contact among
  them. The 20 E5 MISSING items are omissions of an audio-only value.
- 40 items (E4) are knowable from TRAIN's list but were not supplied. They are part of the 79-item vocabulary route.
- By kind, the 229 are 113 MISSING (6.59 pp) and 116 not MISSING (5.80 pp).
- The hearing-visible 71 are mostly E5 (47 items). The consumption 107 are mostly E1 (55).

## 4. Composition and ordering

At measured conversions of forms that can actually be delivered:

- deterministic scope rule at 0.8: **+1.04** (replicate +0.93);
- value-vocabulary route in list form at W4's rate: **+0.24** (W5's 10 items lie inside the 79, so W5 adds nothing on
  top);
- B4 / F10 explicit emptiness: -0.19 net, and it overlaps the scope rule on FP-only rows;
- consumption re-read: about 0 at its only analogue;
- E4 columns: unmeasured.

The best composition of measured parts is **about 1.28 pp** (1.04 + 0.24), and it spans two factors: a deliver-side
edit and a supply change. At M1's printing rate the vocabulary route would add 1.14. That form would need exemplars
that show the value, and speech-keyed retrieval found only 10 of the 79.

**The honest answer: no SLU mechanism clears 1.5 pp at a measured conversion, alone or composed.**

- The largest remaining masses have no measured conversion, or a measured analogue near zero:
  - Solver consumption of supplied or note-carried values: 103 + 107 items, 6.29 + 6.33 pp oracle;
  - hearing: 106 items, 5.13 pp;
  - SPURIOUS deletion: 179 items, 5.76 pp.
- The SLU gap lives on intent-right rows (27.13 of 34.84 points, `docs/results/2026-09-27-slurp-agree-arm-error-sources.md:159`).
  A Solver-side consumption repair there has no same-flight form in Phase 1 (a second Solver visit is cross-flight,
  E4 spec section 4). It therefore needs DEV-2000-ADDED cross-flight reads at 2.5 pp: 42 recovered misses or 82
  removed false positives, converted.
- One exception is structurally same-flight. **E4-1's shadow columns plus the deterministic scope rule applied offline
  to the same sealed columns** form one flight and one decode factor. The rule adds no decode noise. With the rule's
  +1.04, E4's replace-only column would need about 0.09 of its 106-item oracle to bring the composition to 1.5
  ((1.5 - 1.04) / 5.13). Alone it would need 0.29.

## 5. Recommendation to the coordinator

1. **Keep W5 HELD and route it nowhere.** Under decision 192 it is not a cross-flight candidate either:
   - expected 0.15 pp, oracle 0.59;
   - the vocabulary filter lowers both, to 0.10 and 0.41;
   - the whole vocabulary route is 0.24 at the measured list rate;
   - row-matched do-not-tag exemplars are already present for 89 spurious and 81 correct entities, so that form does
     not discriminate.

   *Decision needed:* the owner confirms the W5 line closed (not re-queued cross-flight).
2. **Pre-declare E4-1's information-gain gate before its read.** The gate:
   - replace-only column: net conversion of at least 0.29 of the 106 hearing-plus-re-listen items (oracle 5.13 pp),
     or at least 0.09 when composed with the scope rule;
   - drop column: at least 49.5 net false positives removed (0.28 of the 179 not-in-note SPURIOUS), with harm counted
     on the 273 not-in-note exact items;
   - the blind contact's hearing state is also to be tabulated against this note's E5 / E1 split of the 229.

   *Decision needed:* the coordinator countersigns these gates as the E4-1 read's pre-declared thresholds.
3. **Register a model-free replication read of the deterministic scope rule** (threshold 0.8 and at least 5 pool
   occurrences, both fixed now) on the sealed DEV-2000-ADDED pool, following the EMPTYENT read's form. It reads +1.04 /
   +0.93 on the two Fold A arms. Alone that is under 1.5, so it qualifies only as a deliver-node component composable
   offline, like the normaliser's +1.22 (ledger `:131`).

   *Decision needed:* which bar applies to a deterministic deliver-side edit. The candidates are the 1.5 pp decode
   contrast bar, its own bootstrap interval, or the pool null EMPTYENT used (1.547, `empty-entity :60`), under which
   it would not clear.

## 6. Method and reproduce

- Arm: `SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1` (phases `783299f15626`, outputs `6a4256e09278`, scores `01db05fa5778`).
  Replicate for the scope rule: `SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1` (SLU-F1 64.1566). In-process totals reproduce
  the sealed ones on both arms.
- Knowledge: the flown exemplar pool `size-pool-annotated-exemplars` (9,354 utterances, through `GP.load_exemplar_pool`),
  `slot-contracts-v2` bodies (through `GP.load_contract_bodies`), and the W5 selection `selection-v1.jsonl` with the W5
  snapshot pin. Full SHA-256 values are in `report.json`.
- Vocabulary: utterance-deduplicated TRAIN values outside Fold A, folded with `entity_states.fold`. The class rule is
  the knowledge-content audit's (closed >= 0.9 and semi-closed >= 0.6 leave-one-out coverage), giving 5 closed,
  23 semi-closed and 26 open types.
- Limits:
  - the scope rule's thresholds were set by this author before the first run and were not searched further, but it is
    read on the construction roster;
  - the F10 scaling is proportional per empty-gold FP;
  - W4's 5 of 97 is a cross-flight item delta against the wave A/A.

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_slu_consumption_headroom.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_slu_consumption_headroom.py --check \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
```

Content hashes of the outputs with `generated_at` removed (`content-sha256.json`): `report.json` d72c2dea5b602fe6ea77c2717ce9a26978442bacb32e22e789ae0fd09f3887d7, `tables.md` 71ea9abf61a8ac3f61a619736bfe3e95e755ae7348867c3c33772f9350ad11e3. A `--check` re-run reported IDENTICAL apart from `generated_at`. Driver sha256 at this commit: 19bd6d7ee10de7a493d9d73a9a8144bf13dea8c1645299ec4c5cf85fac34e4bc. Wall time about 7 min (the governed TRAIN loader dominates), peak 0.67 GB.
