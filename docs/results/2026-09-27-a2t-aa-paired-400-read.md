# Cell A2T-AA read: DESCRIPTIVE own null -- h_A2T 1.625 pp on official tool accuracy, 317 of 400 rows byte-identical, request identity 149 of 400 by the recipe's letter (400 of 400 once the dispatch envelope is removed)

Read 2026-09-27 by the analysis agent (Claude Opus 5.5, worktree `/home/chao/saea-worktrees/fable-xcarrier`, branch
`fable/xcarrier`) under the coordinator's brief for the analysis track of owner decision 163. Registered recipe
`docs/readiness/2026-09-27-a2t-stage3-aa-paired-400-v1/analysis-recipe-v1.json` (sha256
`84da9590e9025ce37dbef38f869e4d5776d71501a541b18a5a87515c43a4b023`), read row
`SAEA-A2T-STAGE3-AA-PAIRED-400-READ-V1` registered before any score was read (in the commit 'research: register the A2T-AA read row before reading', which precedes this read on branch fable/xcarrier; first written as 8e6f22e5 before the rebase onto master). Zero model,
tokenizer, encoder, scorer, server, GPU and network contacts: every number below is arithmetic over the two sealed
passes and the sealed direct comparator. DESCRIPTIVE: no verdict, no admission, no bar; the owner disposes
(decision 139).

## 1. What was read

| item | value |
| --- | --- |
| pass A | `SAEA-A2T-STAGE3-AA-PAIRED-400-A-V1` / `attempt-a2t-stage3-aa-paired-400-a-generation-v1`, manifest COMPLETED, attempt FINALIZED |
| pass B | `SAEA-A2T-STAGE3-AA-PAIRED-400-B-V1` / `attempt-a2t-stage3-aa-paired-400-b-generation-v1`, manifest COMPLETED, attempt FINALIZED |
| flight commit | `1cda1a6b` on both passes; empty `study_repo_dirt` on both |
| session | `serving-a2t-native-role-base-np3-max2048-v3` (np3 x 32,768, max_tokens 2048), the same session receipt path on both passes |
| roster | `A2T-PAIRED-400-V1`, 50 rows per tier, split identity `965f145f...0990a`; each manifest's ordered id list equals the roster's |
| comparator (context only) | `SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1` rows of the same 400 ids (2026-09-15, session v2); outputs / scores / manifest hashes equal the recipe's pins |
| driver | `scripts/analysis/a2t_aa_paired_read.py` (sha256 `48392fa5f88a785e2483f441b60f4629483100dcf93da1ae285c1e4df1051d7e`) |
| machine result | `analysis/SAEA-A2T-STAGE3-AA-PAIRED-400-READ-V1/null.json` sha256 `2c7fce43875a30c4a58bb9ad9a27ff898b8cca330492c9d214c7646d4e8a547a`; `per_row.json` sha256 `c7151ef166655478701696989cab6d8203214a37067c0cec36f85f84beb48a56` (ids, tiers, domains, flags, scores and hashes only) |

Every delivered text of both passes re-hashes to its recorded `response_text_sha256` (400 of 400 on each pass).

## 2. Step 2 -- request identity: the recipe's rule is not met by its letter, and why

| quantity | count of 400 |
| --- | ---: |
| `request_sha256` equal between pass A and pass B (the recipe's test) | **149** |
| request content equal once the dispatch envelope is removed (`decoding_params.id_slot`, `request_id`, `history[].contact_id`) | **400** |
| rows that differ ONLY in that envelope | 251 |
| rows whose serving slot differs between the passes | 238 (same slot on 162) |
| rows whose runtime `request_id` differs | 32 |
| trace MODEL_REQUEST `payload_sha256` equal to the outputs row's `request_sha256` | 400 on both passes |

`request_sha256` is the digest of the whole MODEL_REQUEST payload, and that payload carries the serving slot the
dispatcher assigned (`id_slot` in `decoding_params`) and the runtime's request id. On an np3 session the slot is
assigned dynamically, so two request-identical passes agree on the slot only about one time in three. The recipe says
the pair is read as request-identical only at 400 of 400 and that any other count "is reported as the finding and the
null is NOT registered from it". **The finding is therefore reported, and by the recipe's letter h_A2T below is a
measured, descriptive number that is not registered as the carrier's margin.** Whether the envelope-only difference
is accepted as request identity (every model-visible byte is identical on 400 of 400) is the owner's call. The same
envelope makes the recipe's step 2 unsatisfiable on any np > 1 geometry; a future A/A recipe should compare the
content digest with the dispatch envelope removed and keep the raw digest beside it.

## 3. Step 3 -- byte identity

| quantity | value |
| --- | ---: |
| delivered text byte-identical (`response_text_sha256` equal) | **317 of 400 (79.25 %)** |
| byte-identical given the SAME serving slot on both passes | 151 of 162 (93.2 %) |
| byte-identical given a DIFFERENT serving slot | 166 of 238 (69.7 %) |
| official primary tool differs between the passes | 18 |
| official tool verdict differs | 12 |
| official exact-match verdict differs | 8 |

The slot split is the new observation: the delivered answer repeats much more often when the row lands on the same
slot. It matches the SLURP instrument evidence (DET: 50 of 50 identical at np1 with the prompt cache off; ROLL-AA:
91.5 % within one np4 flight): the residual non-determinism is a serving property (slot / batch composition /
cache state), not a request difference.

## 4. Steps 4-5 -- levels and the paired null (pass B minus pass A, tier-stratified paired bootstrap, 10,000 draws, seed 20260903, CI95)

With 50 rows in every tier the natural-mixture and the equal-tier weightings coincide in the point estimate and gave
identical intervals here.

| metric | pass A | pass B | sealed direct (same ids) | B - A (pp) | CI95 (pp) | half-width |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| **official tool accuracy (a2t-toolcall-official)** | 60.75 | 61.75 | 61.75 | +1.000 | [-0.500, +2.750] | **h_A2T = 1.625** |
| official exact match | 15.25 | 16.25 | 15.00 | +1.000 | [-0.250, +2.500] | h_A2T_em = 1.375 |
| repo tool accuracy (a2t-toolcall) | 53.00 | 54.50 | 54.00 | +1.500 | [-0.250, +3.500] | h_A2T_repo = 1.875 |
| official macro parameter F1 | 27.77 | 29.99 | 28.03 | +2.226 | [+0.768, +3.851] | 1.542 |
| official micro parameter F1 | 22.31 | 23.44 | 21.58 | +1.130 | [-0.111, +2.587] | 1.349 |
| repo exact match | 10.00 | 10.75 | 10.00 | +0.750 | [-0.500, +2.000] | 1.250 |
| repo v2 ordered tool accuracy | 52.00 | 53.50 | 53.00 | +1.500 | [-0.250, +3.500] | 1.875 |
| repo v2 exact match | 11.25 | 12.25 | 11.50 | +1.000 | [-0.250, +2.500] | 1.375 |
| official parse rate | 99.75 | 99.25 | 99.75 | -0.500 | [-1.250, 0.000] | 0.625 |

Two cautions travel with these half-widths. (1) They are the null of a within-chain replicate at n = 400, not the
width of a real contrast: the zero-contact re-read of the dual-store rows on the same 400 ids has CI95
[-7.0, +1.5] on tool accuracy (`docs/results/2026-09-27-a2t-earnings-gap-diagnosis.md`, section A6), because a
mechanism moves many more rows than an A/A pair does. (2) The macro parameter F1 difference between two
request-identical passes has a CI95 that excludes zero (+2.23 [+0.77, +3.85]): parameter metrics move on the 83
non-identical rows more than the tool metrics do, so any parameter-F1 claim on this roster needs a margin of at least
this size, not the tool-accuracy one.

## 5. Step 6 -- per tier and per domain

Official columns are the paper protocol (`a2t-toolcall-official`); the repo column is `a2t-toolcall`; the paper
column is arXiv:2604.22821 Table 3, Qwen3-Omni-30B (a published reference, not a matched comparator). 50 rows per
tier, so one row is 2 points.

| tier | identical | tool A / B / direct | paper tool | exact A / B / direct | paper exact | repo tool A / B |
| --- | ---: | --- | ---: | --- | ---: | --- |
| tier1_direct | 41 | 76 / 72 / 76 | 92.4 | 12 / 18 / 14 | 92.4 | 76 / 72 |
| tier2_parametric | 43 | 78 / 82 / 80 | 84.6 | 22 / 24 / 22 | 15.6 | 78 / 82 |
| tier3_multi_intent | 35 | 70 / 74 / 72 | 74.7 | 24 / 24 / 22 | 28.6 | 38 / 42 |
| tier4_implicit | 38 | 24 / 20 / 24 | 33.4 | 2 / 0 / 2 | 11.3 | 24 / 20 |
| tier5_needle | 47 | 86 / 86 / 88 | 90.6 | 22 / 20 / 20 | 36.0 | 86 / 86 |
| tier6_correction | 41 | 62 / 64 / 64 | 81.5 | 8 / 10 / 8 | 24.8 | 58 / 62 |
| tier7_multiturn | 43 | 40 / 42 / 40 | 54.6 | 12 / 12 / 12 | 16.3 | 40 / 42 |
| tier8_intent_blending | 29 | 50 / 54 / 50 | 41.7 | 20 / 22 / 20 | 12.4 | 24 / 30 |

| domain (from the released tier manifests) | rows | identical | tool A / B / direct | exact A / B / direct | repo tool A / B |
| --- | ---: | ---: | --- | --- | --- |
| smart_car | 20 | 15 | 60.00 / 65.00 / 60.00 | 40.00 / 40.00 / 35.00 | 50.00 / 45.00 |
| smart_home | 306 | 240 | 55.88 / 56.54 / 57.19 | 9.80 / 10.13 / 9.48 | 47.06 / 48.69 |
| wearables | 74 | 62 | 81.08 / 82.43 / 81.08 | 31.08 / 35.14 / 32.43 | 78.38 / 81.08 |

Tier 8 (intent blending, multi-call) is the least reproducible tier (29 of 50 identical); tier 5 (needle) the most
(47 of 50). Per-tier deltas of 2-6 points on 50 rows are single-row to three-row movements and carry no weight alone.

## 6. Step 7 -- each pass against the sealed direct rows (context only, never a gate)

| quantity | pass A | pass B |
| --- | ---: | ---: |
| `request_sha256` equal to the 2026-09-15 direct row | 0 of 400 | 0 of 400 |
| request content equal with the envelope removed | 400 of 400 | 400 of 400 |
| delivered text byte-identical to the direct row | 286 of 400 | 281 of 400 |
| official tool accuracy, pass minus direct | -1.000 [-2.750, +0.750] | 0.000 [-1.750, +1.750] |
| official exact match, pass minus direct | +0.250 [-0.750, +1.250] | +1.250 [-0.250, +2.750] |

The comparator flew the same fragment bytes twelve days earlier on session v2; its request digests differ from both
passes only in the dispatch envelope. Cross-day agreement (about 71 % byte-identical) is close to within-chain
agreement (79 %), and neither pass differs from the comparator by more than the within-chain null.

## 7. Step 8 -- throughput (owner decision 140)

| quantity | pass A | pass B |
| --- | ---: | ---: |
| contacts / generation wall (sealed contact window) | 400 / 191.9 s | 400 / 194.8 s |
| contacts per minute | 125.05 | 123.19 |
| prompt tokens per contact | 3,746.6 | 3,746.6 |
| completion tokens per contact | 17.99 | 18.22 |
| prompt tokens per second | 7,808.4 | 7,692.4 |
| slot occupancy (runtime receipt) | 0.654 | 0.652 |
| session monitor inside the window: samples / active s (approx.) / mean W / peak W / mean util | 17 / 144.1 / 66.5 / 92.8 / 58.6 % | 18 / 157.5 / 65.6 / 95.8 / 54.8 % |

The whole 400-row pass costs about 3.2 minutes of generation on np3; the direct-only A2T form is cheap enough to
re-fly as a same-chain A/A beside every future Audio2Tool arm.

## 8. What this read does and does not establish

- It measures the carrier's within-chain replicate noise on the paired 400: h_A2T 1.625 pp (official tool accuracy),
  1.375 pp (official exact match), 1.875 pp (repo tool accuracy), in both weightings.
- By the recipe's letter the null is not registered (request identity 149 of 400); every model-visible byte is
  identical on 400 of 400 and the difference is the dispatch envelope. The owner decides whether these half-widths
  become the registered margins of later Audio2Tool contrasts on this roster (decisions 139, 155, 157).
- No superiority, generalisation, component-causal, bar, admission or confirmatory claim of any kind; A2T-SYS-1's bar
  is not set here.
