# Knowledge-wave item W2, a position-1 guard on the AGREE agreement vote: STOP -- no guard parameter prevents more demotions than it forfeits saves (DESCRIPTIVE)

Date: 2026-09-27. Read id `SAEA-SLURP-STAGE3-W2-AGREE-GUARD-OFFLINE-V1`, recipe `slurp-w2-agree-guard-offline-v1`, owner decision 164 (register W2 if the offline net is positive; otherwise stop and report the curve). **Status: DESCRIPTIVE -- STOP.** No cell was registered, nothing was flipped or flown, no fusion code was changed. A model-free replay: zero model, server, tokenizer, encoder, embedder, network, GPU and paid-API contacts, and no official-scorer subprocess; ports 8080 / 8081 untouched; nothing under `runs/` opened for writing. Gold is read offline on the scoring side only, through `data.slurp.load_slurp_split` on the governed TRAIN split: Fold B gold to tune (TRAIN, allowed), Fold A gold afterwards to count. Every number is a development number (owner decisions 28 and 86). No utterance text, transcript, delivered answer or knowledge body is printed or persisted.

Driver `scripts/analysis/slurp_w2_agree_guard_offline.py` (sha256 `ba8456ec02733e3e2aa740231d9e6cafe2adebddcdfd594872ec8a7b0afa77a2`); outputs `$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-W2-AGREE-GUARD-OFFLINE-V1/` (`report.json`, `tables.md`, `content-sha256.json`). Content sha256 with `generated_at` removed: `report.json` `7c7097a42e4babf01c7acd4433e21e14d315ef723a0b34231aea4889809ed0f2`, `tables.md` `45310ec0885f8b11beaeb87e33f62c44a8589b0a68a200284f724dd6912da3cc`; a `--check` re-run reported IDENTICAL apart from `generated_at`.

## 0. The question and the inputs

The AGREE arm ranks the 60 intent-boundary entries by `cos + 1.0 x vote` (the written-key cosine at recall width 60 plus the self-excluded exemplar-intent vote share) and delivers the first eight (`fuse_coverage` 8-1-8). The error-source read (`docs/results/2026-09-27-slurp-agree-arm-error-sources.md`) found 21 of its 31 harms are demotions of gold, 17 of them from position 1, against 0.82 expected under the same-plan null, with a stated ceiling of up to +1.94 intent. W2 asks whether a guard can keep the pre-agreement position-1 entry `T` (the cosine top) at position 1 where it is confidently ahead, while the term still promotes entries from 2..60 and still delivers new ones.

| input | relpath under `SPEECHRL_DATA_DIR` | sha256 |
| --- | --- | --- |
| intent-boundary store + key vectors | through the rank diagnostic's `load_store` (snapshot content hash `5520b844...`, key vectors `prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl` `76e8d16a...`) | snapshot file `4579079c949e...` |
| Fold A boundary query vectors | `vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl` | `e7a5b2264dc6...` |
| Fold A agreement table (the one AGREE flew) | `prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl` | `018ca6ef0d10...` |
| Fold B boundary query vectors | `vectors/slurp-intent-boundaries-train-fold-b-1080-v1/query-vectors-speech-segments.jsonl` | `83c5da6190fb...` |
| Fold B agreement table (filler family) | `prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FILLER-FOLD-B-V1/agreement.jsonl` | `06990a86d204...` |
| AGREE sealed phases / scores | `runs/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/...` | phases `783299f15626...`, scores `01db05fa5778...` |
| A/A sealed phases / scores | `runs/SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1/...` | phases `26e964aabc14...`, scores `66cb7ab22bc9...` |
| error-source rows (transition class per flip row) | `analysis/SAEA-SLURP-STAGE3-AGREE-ERROR-SOURCES-V1/rows.jsonl` | `17a0be507949...` |

**Structural check.** The offline replay reproduces AGREE's sealed eight-entry block in order on **1080/1080** Fold A rows and the A/A's sealed block (the cosine order) on **1080/1080**, using the agreement table the runtime read. On Fold B 1,078 of the 1,080 agreement rows carry a boundary query vector (2 do not and are left out); one row per fold recalls a single candidate.

## 1. The guard families and the tuning rule (fixed before Fold A gold was read)

`T` = the cosine order's top, `C` = the agreement order's top. Pinning puts `T` first and keeps the agreement order for every other entry.

| family | parameter | rule |
| --- | --- | --- |
| `cos-margin-pin` | delta | pin `T` when `cos[T] - cos[second]` >= delta (the boundary channel's own pre-agreement margin) |
| `incumbent-bonus` | h | rank by `cos + vote + h x [entry == T]` (the term must beat the incumbent by more than h) |
| `vote-lead-pin` | lead | pin `T` unless `vote[C] - vote[T]` >= lead (grid on midpoints of the 1/20 and 1/19 vote lattices, so no lead sits on a float edge) |

**Rule.** On TRAIN Fold B only, choose the family and parameter that maximise the model-expected intent change against the unguarded term, where a row's expected correctness is P(intent correct | gold at block position p) from the gold-position read's DEV-2000-ADDED column (`docs/results/2026-09-26-slurp-gold-position-and-solver-freedom-read.md` table B.1: 98.0 / 81.9 / 74.5 / 54.8 / 61.9 / 77.3 / 53.3 / 41.2 % at positions 1-8, 19.5 % undelivered -- a roster disjoint from both folds); ties go to the rule that changes fewer blocks. No Fold A number enters the choice.

## 2. Fold B: the tuning curve

Under the same curve the unguarded term is worth +9.30 pp over the cosine order on Fold B (a delivery-model number, not an accuracy measurement). Where the term changes the top (402 rows), gold is the challenger `C` on 202, the incumbent `T` on 60, neither on 140.

| family | best parameter | blocks changed | gold to position 1 | gold off position 1 | model delta, rows | pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `vote-lead-pin` | **0.225** (pin unless the vote leads by 5+ of 20) | 74 | 30 | 20 | **+1.67** | **+0.155** |
| `incumbent-bonus` | 0.1 | 239 | 24 | 10 | +1.30 | +0.120 |
| `cos-margin-pin` | 0.05 (tied 0.08) | 25 | 12 | 7 | +0.88 | +0.082 |

Every family peaks between +0.08 and +0.16 pp and turns negative as the guard widens (full pin: -2.55 pp, 202 gold entries pushed off position 1 against 60 restored). **Chosen by the rule: `vote-lead-pin`, lead 0.225.** The full curves (38 points) are in `tables.md`.

## 3. Fold A: the trade-off (gold offline, counts only)

AGREE's sealed flips against its in-chain A/A: 31 harms (21 demotions, 17 of them from position 1) and 67 saves (32 gold newly delivered, 28 gold promoted).

**The chosen rule on Fold A:**

| quantity | value |
| --- | ---: |
| blocks changed against AGREE | 65 of 1,080 |
| demotion harms prevented (gold returned to its pre-agreement position 1) | **5 of 21** |
| delivery saves forfeited (gold moved below where AGREE put it) | **7 of 60** -- newly delivered 6 of 32, promoted 1 of 28 (moves 1->2: 5, 2->3: 1, 4->5: 1) |
| other harms helped / other saves hit | 0 / 0 |
| prevents more than it forfeits | **no** (5 < 7) |
| expected intent change, position read only | +2.39 rows = +0.22 pp |
| expected intent change, newly delivered rows at the CONV conversion (32/70 over the 77.83 % position-matched prior, scale 0.587) | +3.10 rows = **+0.29 pp** |
| same at the KPROBE conversion (24/55, scale 0.561) | +3.14 rows = +0.29 pp |

The expectation values every row whose block changes, not only the sealed flip rows: gold entries delivered before the term (promotions and demotions) at the gold-position read's Fold A PLAN rates (98.7 / 73.9 / 61.5 / 63.3 / 38.5 / 58.8 / 70.0 / 72.7 % at 1-8, 21.1 % undelivered), newly delivered ones at that rate times the measured conversion scale.

**The whole curve on Fold A** (evaluation, not selection): at **no** point of any family does the guard prevent more harms than it forfeits saves. The closest points reach parity -- `vote-lead-pin` 0.125 (1 / 1) and 0.175 (4 / 4), `cos-margin-pin` 0.08 (1 / 1) -- and every wider guard forfeits more: `vote-lead-pin` 0.275 prevents 7 and forfeits 12, 0.325 prevents 8 and forfeits 20, the full pin prevents 17 and forfeits 61. The largest expected change anywhere on the curve is +0.31 pp (`vote-lead-pin` 0.275). Nothing approaches the 2.5 pp floor at n = 1,080.

| family | parameter | blocks changed | harms prevented /21 | saves forfeited (new /32 + promoted /28 + other) | expected pp (position / CONV) |
| --- | ---: | ---: | ---: | --- | --- |
| `vote-lead-pin` | 0.075 | 15 | 0 | 0 | +0.14 / +0.14 |
| `vote-lead-pin` | 0.125 | 29 | 1 | 1 + 0 + 0 | +0.16 / +0.18 |
| `vote-lead-pin` | 0.175 | 44 | 4 | 3 + 1 + 0 | +0.18 / +0.22 |
| `vote-lead-pin` | **0.225** | 65 | 5 | 6 + 1 + 0 | +0.22 / +0.29 |
| `vote-lead-pin` | 0.275 | 90 | 7 | 7 + 4 + 1 | +0.23 / +0.31 |
| `vote-lead-pin` | 0.325 | 125 | 8 | 13 + 6 + 1 | -0.14 / +0.03 |
| `vote-lead-pin` | 0.55 | 228 | 14 | 21 + 12 + 2 | -0.80 / -0.49 |
| `incumbent-bonus` | 0.1 | 192 | 2 | 4 + 5 + 1 | +0.01 / +0.09 |
| `incumbent-bonus` | 0.2 | 234 | 7 | 10 + 6 + 2 | +0.08 / +0.23 |
| `cos-margin-pin` | 0.05 | 31 | 1 | 3 + 1 + 1 | +0.02 / +0.05 |
| `cos-margin-pin` | 0.02 | 112 | 5 | 11 + 8 + 1 | -0.57 / -0.45 |
| any family, full pin | -- | 368 | 17 | 31 + 28 + 2 | -3.18 / -2.68 |

## 4. Why: the harms carry the saves' signature

The 17 position-1 demotion harms and the 47 saves whose gold became the new top over a wrong incumbent, by the two signals a guard can read before the answer:

| signal | bin | position-1 demotion harms (17) | saves, gold the new top (47) |
| --- | --- | ---: | ---: |
| vote lead of `C` over `T` | 2 votes | 1 | 1 |
| | 3-4 votes | 4 | 4 |
| | 5-6 votes | 3 | 8 |
| | 7+ votes | 9 | 34 |
| cosine margin of `T` over the second entry | < 0.01 | 6 | 25 |
| | 0.01-0.03 | 8 | 14 |
| | 0.03-0.06 | 2 | 7 |
| | >= 0.06 | 1 | 1 |

In no bin of either signal do the harms outnumber the saves; where the guard would have to act to reach most harms (a vote lead of 5+ votes, 12 of 17), the saves outnumber them 42 to 12. The same holds over every row where the term changes the top: on Fold A gold is the challenger on 192 and the incumbent on 69, and at a lead of 7+ votes 155 to 31; on Fold B 202 to 60 and 164 to 20. A demotion harm is the row where the exemplar pool is confidently wrong, and neither the vote nor the boundary cosine can tell that row from the rows where it is confidently right. The error-source read's "+1.94 ceiling" is the oracle value of the 21 harms; a guard that reads only these signals realises about +0.2-0.3 pp of it and pays for it in saves.

## 5. Consequence

W2 is **not registered**: by the owner's stop rule (no guard parameter prevents demotions without forfeiting at least as many saves) and on its own expectation (+0.29 pp at the Fold-B-tuned point, an order of magnitude under the 2.5 pp floor at n = 1,080; even as a no-harm registration it would buy nothing measurable). No `rails/` change was made, so the AGREE arm's prepared supply and every committed identity are untouched. What would separate the demotion rows needs evidence outside the vote and the boundary cosine -- the "discriminative consumption" and "contrastive knowledge content" rows of the error-source read's capability table -- not a rank guard.

## 6. Reproduce

```bash
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_w2_agree_guard_offline.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/analysis/slurp_w2_agree_guard_offline.py --check \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
```
