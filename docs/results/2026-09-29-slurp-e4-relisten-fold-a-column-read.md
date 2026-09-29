# Cell E4-1 same-flight shadow-column read on TRAIN Fold A: both re-listen columns lose official SLU-F1 against the delivered column (replace-only -4.11 pp CI95 [-5.41, -2.88]; replace + drop-when-unheard -3.59 pp [-5.08, -2.14]); neither clears its pre-declared gate (DESCRIPTIVE)

Read on 2026-09-29 by the records and read agent (Claude Opus 5.5, on the coordinator's brief, Fable 5.1), in
worktree `fable/e4read`. The read is model-free. `core.flight.cli` and `lease_cli` were not invoked. There were no
model, server, encoder, embedder, tokenizer or GPU contacts. Two official column scorings ran
(`slurp-slu-official-train`, one complete derived copy each, never sharded). The read ran as a CPU sidecar while
the queue driver flew COMP-1b.

The READ row `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1` and its SEAL-ONLY READING CLAUSE were root
countersigned on master at `dfb5c0121` (2026-09-29T19:07:33Z). That was after the seal and before any column score
was opened. The root act was delegated by the coordinator. The pre-declared gate sentence in that row is unchanged.
The recipe is `docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-resume-v1/analysis-recipe-v1.json`
(recipe id `slurp-stage3-relisten-fold-a-sealonly-column-analysis-v1`, owner decision 194). It is a paired row
bootstrap: cluster key `sample_id`, 10,000 draws, seed 20260915.

No utterance text, gold label, slot filler, relisten value or model output was printed or persisted. Only counts,
rates, pp, slot TYPE names, scenario names, ids and hashes appear below.

**DESCRIPTIVE.** These are development numbers on a TRAIN construction fold (owner decisions 28 and 86). They are
never a test claim, a generalisation claim or a system-level claim. The claim ceiling is `nominated`. The verdict
word belongs to the coordinator (decision 139).

## 1. What was sealed

| item | value |
| --- | --- |
| arm run | `SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1` |
| sealed attempt | `attempt-slurp-native-stage3-relisten-fold-a-generation-v1-seal-only` (owner decision 194) |
| flight commit, queue | `0b50d47e`, `queue_e4seal.sh`; `SEALONLY-E4 DONE 2026-09-29T16:36:24Z`, chain exit 0 |
| manifest | COMPLETED, `study_repo_dirt` empty; 1,080 rows kept from `attempt-slurp-native-stage3-relisten-fold-a-generation-v1`, 0 flown, 0 new contacts |
| predecessor trace | `966613e4...f233f6` (re-hashed by the read) |
| run manifest / outputs / scores sha256 | `eef74918...4b12e5` / `1324ddc8...57bfc2e` / `5277961f...48584` |
| backfilled read inputs (model-free, `scripts/analysis/backfill_sealonly_read_inputs.py`, master `70b67bbfc`) | generation manifest `39cb9fef...ad85`, phases `0db1174f...ebb7` |

Flight cost, summed over the predecessor's contacts by the backfill: 6,304 contacts, 18,730.523 speech s,
42,480,069 prompt / 290,668 completion tokens, 23,839.8 s summed call latency, 0 tool calls.

## 2. How the read ran (two read-path defects, fixed on this branch before any score was opened)

1. **The attempt.** `scripts/flights/e4/e4_read.sh` hard-coded the aborted attempt. It now reads the seal-only
   attempt under the seal-only recipe id. It refuses unless the manifest is COMPLETED and names predecessor trace
   `966613e4...`. `E4_ATTEMPT` overrides the attempt.
2. **AT1 refused on row 1.** 976 of the 1,080 sealed delivered texts are the core's own compact JSON (key order
   scenario/action/entities). The other 104 are the sorted-key canonical render. All 976 parse to the same payload.
   The render compared a canonical re-render with the sealed bytes, so it could never match those 976 rows. A column
   whose bound entity list equals the delivered list now keeps the sealed text byte for byte. The canonical render is
   used only for a column that `bind()` changed. The official scorer parses the JSON, so key order moves no score.
3. **No blind trace.** The seal-only attempt's own trace is empty (0 records). Every kept row's relisten contacts live
   in the predecessor trace. `relisten_main` now re-derives the declared predecessor with
   `core.bundle.outputs.verify_predecessor_attempts`, the same I7r re-hash that `verify_bundle` uses. The render
   looks a contact up in the bundle's own trace first, then in that row's own predecessor records only. The render
   manifest source names the predecessor attempt and trace hash.

Items 2 and 3 are code changes in `scripts/analysis/stage3_rollout_score.py`. Each has a unit test in
`tests/unit/test_e4_targeted_relisten.py` (229 passed, `-k "relisten or rollout_score or e4"`). Both refusals
happened inside the render, before any file was written, and no score was opened by either.

Render receipt: 1,080 rows, 1,015 entities triggered, 1,889 relisten contacts, AT1 checked on 1,897 row-columns.
Render manifest `11bae1cf...d0`; shadow copies: replace-only `ab602269...c25f`, replace + drop `89279823...1ce7`;
score summary `62322990...0a69`.

## 3. The two contrasts (shadow column minus delivered column)

**Intent is identical by construction, and the read tested it.** The intent guard found 0 of 1,080 rows differing in
(parsed, scenario, action) for either column. Intent accuracy is 85.74 % on all three columns: delta 0.00, CI95
[0.00, 0.00].

| column | official pooled SLU-F1 delivered -> shadow | delta pp | CI95 pp | CI90 pp | row SLU-F1 saves / harms / ties | span-F1 delta pp |
| --- | --- | ---: | --- | --- | --- | ---: |
| relisten-replace-only | 64.02 -> 59.91 | **-4.11** | [-5.41, -2.88] | [-5.19, -3.05] | 14 / 66 / 1,000 | -6.22 [-8.15, -4.40] |
| relisten-replace-drop-unheard | 64.02 -> 60.42 | **-3.59** | [-5.08, -2.14] | [-4.83, -2.39] | 17 / 83 / 980 | -5.57 [-7.62, -3.54] |

| weighting | replace-only SLU-F1 pp | replace + drop SLU-F1 pp |
| --- | --- | --- |
| natural mixture | -4.11 [-5.41, -2.88] | -3.59 [-5.08, -2.14] |
| equal scenario | -3.92 [-4.96, -2.77] | -3.13 [-4.51, -1.62] |

By channel, replace-only is far-field -1.89 and headset -1.56 row-SLU pp. Replace + drop is -2.61 and -2.76.

### Per-scenario SLU-F1 (delivered -> shadow, delta pp, CI95)

| scenario | n | replace-only | replace + drop |
| --- | ---: | --- | --- |
| alarm | 60 | 72.46 -> 55.76, -16.69 [-24.67, -8.66] | 72.46 -> 55.76, -16.69 [-24.67, -8.66] |
| audio | 60 | 62.95 -> 62.54, -0.41 [-5.31, 3.81] | 62.95 -> 67.21, +4.26 [-3.41, 12.38] |
| calendar | 60 | 67.62 -> 60.60, -7.02 [-11.73, -2.37] | 67.62 -> 60.16, -7.47 [-12.25, -2.84] |
| cooking | 60 | 61.11 -> 61.11, 0.00 | 61.11 -> 61.35, +0.24 [-2.96, 3.01] |
| datetime | 60 | 74.07 -> 67.00, -7.07 [-15.23, 0.00] | 74.07 -> 67.81, -6.26 [-15.01, 1.86] |
| email | 60 | 61.78 -> 55.92, -5.87 [-11.83, -1.23] | 61.78 -> 56.77, -5.01 [-11.17, 0.04] |
| general | 60 | 27.27 -> 27.27, 0.00 | 27.27 -> 27.03, -0.25 [-11.08, 7.26] |
| iot | 60 | 66.37 -> 53.28, -13.09 [-22.07, -3.48] | 66.37 -> 55.11, -11.25 [-21.03, -0.45] |
| lists | 60 | 62.43 -> 53.12, -9.32 [-15.24, -3.12] | 62.43 -> 54.27, -8.16 [-14.52, -1.17] |
| music | 60 | 47.53 -> 45.24, -2.29 [-7.72, 0.15] | 47.53 -> 51.01, +3.47 [-4.11, 10.99] |
| news | 60 | 65.59 -> 64.73, -0.86 [-2.92, 0.00] | 65.59 -> 62.31, -3.28 [-8.01, 0.09] |
| play | 60 | 53.33 -> 52.52, -0.81 [-3.29, 1.52] | 53.33 -> 53.00, -0.34 [-4.14, 3.20] |
| qa | 60 | 63.82 -> 63.82, 0.00 | 63.82 -> 66.40, +2.58 [0.47, 5.62] |
| recommendation | 60 | 68.64 -> 67.20, -1.45 [-3.68, 0.00] | 68.64 -> 67.20, -1.45 [-3.68, 0.00] |
| social | 60 | 58.73 -> 59.89, +1.16 [0.00, 3.08] | 58.73 -> 61.08, +2.35 [-0.89, 5.48] |
| takeaway | 60 | 59.45 -> 57.28, -2.17 [-4.20, -0.58] | 59.45 -> 57.59, -1.86 [-4.03, -0.09] |
| transport | 60 | 65.23 -> 62.35, -2.88 [-7.47, 0.24] | 65.23 -> 63.07, -2.16 [-6.82, 1.34] |
| weather | 60 | 78.72 -> 76.92, -1.81 [-5.62, 0.13] | 78.72 -> 73.68, -5.04 [-12.34, 0.05] |

## 4. Where the loss comes from: per-entity-class transitions

Gold-side item states come from `analysis.sealed_credit.entity_states.entity_items`. Gold is read offline on the
scoring side only. Counts are over the 941 gold entities of the 1,080 rows.

| gold-side state | delivered | replace-only | replace + drop |
| --- | ---: | ---: | ---: |
| EXACT | 528 | 467 | 457 |
| BOUNDARY | 69 | 127 | 127 |
| FORMAT | 9 | 13 | 13 |
| NEAR | 56 | 51 | 47 |
| WRONG-VALUE | 43 | 47 | 42 |
| WRONG-TYPE | 57 | 58 | 58 |
| MISSING | 179 | 178 | 197 |
| SPURIOUS (pred side) | 258 | 257 | 208 |

The transitions that moved in the replace-only column:

- EXACT -> BOUNDARY 63
- EXACT -> NEAR 3
- EXACT -> WRONG-VALUE 2
- BOUNDARY -> EXACT 5
- NEAR -> EXACT 2
- BOUNDARY -> FORMAT 4
- NEAR -> FORMAT 2
- NEAR -> WRONG-VALUE 3
- FORMAT -> BOUNDARY 2
- NEAR -> BOUNDARY 1
- WRONG-VALUE -> BOUNDARY 1
- MISSING -> WRONG-TYPE 1

**The mechanism's own failure is span, not hearing.** 63 of the 122 accepted replacements turned an EXACT delivered
value into a BOUNDARY value. The blind contact returns the heard phrase with a different span than the gold
annotation. The largest types:

- date 11
- time 10
- timeofday 9
- house_place 5
- list_name 5
- color_type 4
- food_type 4
- relation 4
- place_name 3
- time_zone 3

Only 7 accepted replacements repaired an item to EXACT. The drop column adds the drops on top of that same loss.

## 5. The pre-declared information-gain gate (coordinator, 2026-09-29, before any read)

Driver: `scripts/analysis/slurp_e4_relisten_gate_read.py` (new on this branch; model-free).

- Output: `analysis/SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1/gate/`
  (`report.json` `336670bc...2c7f`, `tables.md` `2ac5c7de...89c2bf`).
- It re-derives the AGREE-defined sets exactly as the headroom read did. They reproduce: hearing 71, re-listen
  contiguous 35, union 106, SPURIOUS 253, not-in-note SPURIOUS 179, not-in-note EXACT 273.
- Gold-side items are keyed by (sample id, gold index), which does not depend on any arm's prediction. So the 106
  set is read directly on E4-1's columns. Pred-side SPURIOUS items do not transfer across arms. The drop gate is
  therefore read on E4-1's own delivered column under the same definitions: the note is E4-1's own Perception note,
  read from the predecessor trace's ORG records. On E4-1 the analogues are 174 not-in-note SPURIOUS and 267
  not-in-note EXACT.

| gate | pre-declared threshold | measured | result |
| --- | --- | --- | --- |
| replace-only: net conversion over the 106 hearing-visible + re-listen-addressable items | >= 29 % | 106 items, of which 101 are errors and 5 are EXACT in E4-1's delivered column; 4 converted to EXACT, 1 broken; net 3 = **2.83 %** (12 changed state) | **not met** |
| drop-when-unheard: net false positives removed, harm on the correct items absent from the Perception note | >= 49.5 | 68 entities dropped. Of these, 48 were SPURIOUS removed (43 not in the note, 5 in the note), 10 were EXACT lost (8 not in the note) and 10 were partial matches lost (NEAR 4, WRONG-VALUE 5, WRONG-TYPE 1). Net **40** (48 - 8), or 38 with every EXACT loss counted | **not met** |

On the AGREE-defined 273 keys, 248 are EXACT in E4-1's delivered column. The drop column, which includes the
replacements, loses 26 of those 248.

## 6. Relisten receipts and cost

| quantity | value |
| --- | ---: |
| rows with a relisten receipt | 1,080 |
| entities triggered | 1,015 (the seal rehearsal's figure, confirmed) |
| relisten contacts | 1,889 (confirmed) |
| accepted replacements | 122 (confirmed) |
| blind dispositions | value 336, unheard 679 |
| confirm contacts fired | 874 |
| confirm votes | delivered 684, candidate 176, neither 14 |
| drop rule (blind unheard and confirm votes unheard) | 68 |

Accepted replacements by type:

- time 22
- date 13
- timeofday 12
- food_type 7
- house_place 6
- place_name 6
- list_name 5
- podcast_descriptor 5
- one to four each on 21 more types

**Cost of the relisten stage.** This is the predecessor trace's COST records, joined to roles through the response
hashes of the `native-role-contact` records:

| quantity | relisten | rest of the flight | relisten share |
| --- | ---: | ---: | ---: |
| contacts | 1,889 | 4,415 | 29.96 % |
| contacts per row | 1.749 | 4.088 | -- |
| speech seconds | 6,096.6 | 12,633.9 | 32.55 % |
| prompt tokens | 4,502,291 | 37,977,778 | 10.60 % |
| summed server compute (prompt + predicted ms), h | 0.497 | 5.607 | 8.14 % |
| summed call latency, s | 2,179.9 | 21,659.8 | 9.14 % |

GPU-h cannot be read from a serving monitor for this arm. The seal-only attempt served nothing, and the aborted
attempt sealed no `seal` stage. The contact-summed compute overstates wall time at np4.

## 7. Verdict (read agent, for the coordinator)

**Verdict (read agent, for the coordinator):**

- **relisten-replace-only: SHADOW HARM** under the recipe's rule. The CI95 upper bound -2.88 is below zero, and the
  point magnitude 4.11 exceeds the provisional null 0.3163 pp.
- **relisten-replace-drop-unheard: SHADOW HARM.** The upper bound is -2.14 and the magnitude is 3.59.
- **Pre-declared gate: NOT NOMINATED on both columns.** Replace-only net conversion is 2.83 %, against 29 %. The drop
  column removes 40 net false positives, against 49.5.
- Intent is identical by construction (0 of 1,080 rows differ).
- The loss is the blind contact's span: 63 EXACT -> BOUNDARY among 122 accepted replacements, mostly on
  date / time / timeofday. Hearing is not the source of the loss.
- The drop rule alone is net positive in items. Relative to replace-only it removes 48 SPURIOUS for 10 EXACT lost,
  and SLU-F1 is +0.51 pp between the two columns. It still sits under its gate.

The coordinator's clause and the disposition are pending. Nothing is admitted, and no flight is authorised.

## 8. Reproduce

```bash
# model-free; worktree fable/e4read
SAEA_REPO_ROOT=$PWD bash scripts/flights/e4/e4_read.sh            # refuses if pass directories already hold files
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/src python -B scripts/analysis/slurp_e4_relisten_gate_read.py \
    --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
```

Pass verdict sha256: replace-only `d2bf94c7...0c93`, replace-drop-unheard `7079c1db...473f`.

## Coordinator verdict (Fable 5.1, 2026-09-29)

- **E4-1 core-native targeted re-listen v1: NOT NOMINATED, SHADOW HARM on both columns.** Replace-only SLU-F1 -4.11 [-5.41, -2.88]; replace + drop-when-unheard -3.59 [-5.08, -2.14]; neither pre-declared gate is met (net conversion 2.83 % of the 106 addressable items against 29 %; 40 net false positives removed against 49.5). Intent identical by construction. Development number (decisions 28/86).
- **Mechanism reading.** The core cannot verify its own hearing by blind + forced-choice re-listen: 63 of the 122 accepted replacements turned an exact value into a BOUNDARY one (date, time, timeofday) and only 7 turned an item exact. The drop half of the mechanism is the only positive part (SPURIOUS 258 -> 208, 8 correct items lost), worth about +0.8 pp offline as a drop-only column, under the 1.49 pp same-flight SLU floor.
- **Line status.** Core-native replacement re-listen is CLOSED. Per owner decision 180's sequence ("core-native first, Whisper after the E4 read"), the next verification route is the frozen tool-level ASR (Whisper) as a pinned, logged tool for slot VALUE verification; this needs an owner decision (proposed 201) because it is a new tool contact class. A drop-only shadow column may ride as a descriptive column beside a later cell; it is not registered on its own.
