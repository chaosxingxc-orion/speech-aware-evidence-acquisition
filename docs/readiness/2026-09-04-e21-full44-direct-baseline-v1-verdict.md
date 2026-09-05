# Earnings-21, all 44 discovery calls, bare-core direct baseline — verdict

**ALIGNED.** The bare frozen Qwen3-Omni-30B-A3B-Instruct Q4_K_M core transcribes the **whole**
Earnings-21 discovery corpus at **8.200 % corpus WER under the Whisper `EnglishTextNormalizer`**,
against `openai/whisper-large-v3`'s published **9.71** on the same 44 files — **1.51 points better**,
inside the owner's 3-point band, and under every degraded-model floor including the strict one
(Whisper medium.en 10.2).

The number is now unconditional. All 44 calls, 39.26 h, 1,593 fixed 90-second windows, one build,
one serving geometry, one audio path, one instruction — and the paper-facing metric comes out of
`core.scoring_batch`'s **verified** path off a manifest that declares it, not out of an out-of-band
read.

| | |
|---|---|
| run | `SAEA-E21-FULL44-DIRECT-BASELINE-V2`, attempt `attempt-20260904T233816Z-bcd338` |
| study commit at the flight | `44db2e9d` |
| config hash | `e4b133d1df5611b4e0676cf143de07f7b9b2831ffbd247daf20e6263dfc460ae` |
| protocol hash | `06f7f3080f62a065f9c4ec76c58133161ed000412f864595d29a5ed777330145` |
| build | `04ccc72a2207347ca76161b93fd9d846dd0a8675`, bf16 mmproj resident on the GPU |
| geometry | `-c 36864 -np 6`, 6,144 tokens per slot, `GGML_CUDA_DISABLE_GRAPHS=1` |
| population | `earnings21-original` discovery, 44 calls, identity `fcc1b0bc…d69e` |
| protocol | bare-core, no evidence, fixed 90-s windows, no VAD trim, no overlap, no rolling tail, greedy, `max_tokens` 1024 |
| manifest scorers | `asr-wer-whisper`, `asr-wer`, `entity-wer`, `cost` |
| preregistration | `docs/readiness/2026-09-04-e21-full44-direct-baseline-v1-preregistration.md` |
| numbers | `docs/checks/speech-aware-evidence-acquisition/2026-09-04-e21-full44-direct-baseline-v1/verdict/result-summary.json` |

## 1. The number, and the preregistered rule applied to it

| metric | value |
|---|---:|
| **corpus WER, Whisper normalizer, all 44 (paper-facing)** | **8.200 %** |
| mean of per-call WER, Whisper normalizer | 8.004 % |
| substitutions / deletions / insertions | 13,098 / 5,701 / 10,700 |
| reference words after the Whisper normalizer | 359,765 |
| corpus WER, frozen `saea-scoring-v1` | 12.588 % |
| mean of per-call WER, `saea-scoring-v1` | 12.547 % |

* **band test** — 8.200 ≤ 12.71 (9.71 + 3.0): **PASS**
* **strict floor test** — 8.200 ≤ 10.2 (Whisper medium.en): **PASS**
* ALIGNED-BETTER would need < 6.71: **not reached**
* → **ALIGNED**

| published target | published | ours | delta |
|---|---:|---:|---:|
| `openai/whisper-large-v3` — Open ASR Leaderboard long-form, all 44 | 9.71 | 8.200 | **−1.51** |
| Whisper large-v2 — Whisper paper App. D.4, all 44 | 9.7 | 8.200 | −1.50 |
| TRADE speech-LLM — arXiv:2606.08486 Table 2 | 9.75 | 8.200 | −1.55 |
| FastConformer FT+LCA+GT — same table | 13.84 | 8.200 | −5.64 |

| degraded-model floor | published | cleared |
|---|---:|---|
| Whisper medium.en (strict) | 10.2 | yes, by 2.00 |
| Whisper small.en | 10.8 | yes |
| Whisper base.en (loose) | 12.5 | yes |
| Whisper tiny.en | 17.0 | yes |
| FastConformer FT+LCA+GT | 13.84 | yes |
| Qwen2-Audio-7B (normalizer unnamed; a floor only, never a target) | 26.06 | yes |

The `saea-scoring-v1` figure is printed for continuity with this repository's own history and is
**not comparable** to any published row: a different normalizer family. That it also lands near 9.71
is a coincidence between two unrelated normalizers and must never be read as a second alignment.

## 2. `4346923`, the call the 10-of-44 subset excluded

| | corpus WER |
|---|---:|
| all 44 | **8.200** |
| the 43 without `4346923` | 7.888 |
| **its cost to the corpus number** | **+0.312 points** |

`4346923` — Cementos Argos, Industrial Goods, **16 kHz**, 78.5 min, 53 windows — scores **18.94 %**
on its own: the worst of the 44 and more than twice the corpus figure. The Earnings-21 paper singles
it out as degrading every published system, and it degrades this one too. It is inside the number
now, which is the entire point: every published row carries it.

## 3. The ten sealed calls, re-measured on this build

| | corpus WER |
|---|---:|
| the ten, sealed 2026-08-14 — build `5d9dfcb58`, mmproj on the CPU | 7.137 |
| **the same ten, this flight** — build `04ccc72a`, mmproj on the GPU | **7.185** |
| delta | **+0.048** |
| the other 34, this flight | 8.470 |

The build change and the audio-path change were made in the same step and this flight does not
separate them. Together they move the ten by **five hundredths of a point**. So the distance from
the old conditional 7.137 to the new unconditional 8.200 is **not** a build effect and not an
audio-path effect: it is the corpus. The 34 calls the subset never touched are simply harder —
8.470 against 7.185 under an identical protocol on the same day.

That is the honest reading of the August number: 7.137 was right about what it measured, and what it
measured was the easier half of the corpus.

## 4. Strata

Natural mixture is the corpus number, 8.200, in both tables.

| sector | calls | corpus WER |
|---|---:|---:|
| Services | 5 | 6.468 |
| Consumer Goods | 5 | 7.052 |
| Conglomerate | 4 | 7.361 |
| Healthcare | 5 | 7.992 |
| Utilities | 5 | 8.046 |
| Basic Materials | 5 | 8.437 |
| Financial | 5 | 8.723 |
| Technology | 5 | 9.153 |
| Industrial Goods | 5 | 10.662 |
| **equal-stratum mean** | | **8.210** |

| sample rate | calls | corpus WER |
|---|---:|---:|
| 44,100 Hz | 7 | 7.046 |
| 24,000 Hz | 21 | 7.320 |
| 22,050 Hz | 5 | 7.577 |
| 16,000 Hz | 6 | 10.737 |
| 11,025 Hz | 5 | 11.078 |
| **equal-stratum mean** | | **8.752** |

Re-weighting the sectors equally moves the number by 0.01 points. Re-weighting the sample rates
equally moves it by 0.55, and in the obvious direction: the two low-rate strata carry a ~3.5-point
penalty against the three higher ones, and the corpus is 64 % 24 kHz-or-better by call count.
**Under either weighting the verdict is unchanged** — ALIGNED, strict floor cleared.

The sector ordering should be read with 4–5 calls per level; Industrial Goods is worst partly
because it contains `4346923`.

## 5. Entity WER

**Mention-level `1 − recall`** over the `.nlp` `wer_tags` sidecar under the frozen
`normalize_text_v1` — **its own normalizer, not the Whisper one** — so precision is 1.0 by
construction and only the recall-derived error rate carries information. `fstalign` was not
installed and not run; **nothing here is comparable to ConEC's fstalign-based Table 2**, and no
comparison to it is drawn.

Corpus entity WER **30.36 %** over **38,366 gold mentions** (macro 31.51 %), 27 classes.

| class | entity WER % | gold mentions |
|---|---:|---:|
| LOC | 4.3 | 323 |
| NORP | 10.8 | 212 |
| GPE | 22.2 | 1,287 |
| ORG | 25.4 | 2,871 |
| PERSON | 27.3 | 2,212 |
| EVENT | 41.4 | 263 |
| FAC | 46.3 | 41 |
| PRODUCT | 48.8 | 217 |
| `__UNTYPED__` | 0.0 | 1 |

The eight rows above the sentinel are ConEC's non-numeric classes, listed so the shape is visible;
the remaining 18 classes (numeric, temporal and orthographic) are in `result-summary.json`. FAC's 41
mentions make that row directional at best.

**`__UNTYPED__` is a corpus defect made visible, not a metric.** Call `4320211`'s `.nlp` tags one
token with entity id `1057` while its `wer_tag.json` sidecar carries only ids 0–904 — **one id of
38,377 across the 44 calls, one tagged token of 55,294**. It is an annotation gap in the Earnings-21
release. Section 8 explains what it cost and what was done about it.

## 6. Cost and throughput

| | |
|---|---:|
| windows (model contacts) | 1,593 of 1,750 planned |
| speech audio | 141,345.85 s = **39.263 h** |
| **GPU seconds / hours** | 3,504.4 / **0.973** |
| ceiling | 4.0 GPU-h |
| peak VRAM | 22,720 MiB of 24,463 |
| prompt / completion tokens | 1,935,965 / 439,532 |
| skipped slices / saturated slices | **0 / 0** |
| CPU seconds | 332.3 |
| decode wall | about 90 min at ~17.5 windows/min |
| realized realtime factor | **40.3× realtime** (39.26 h of audio in 0.973 GPU-h) |

The GPU-resident mmproj is what made the flight affordable: the sealed August arm needed 89.15 s of
wall latency per window with the encoder on the CPU; this flight's smoke measured **16.29 s**, a
**5.47× speedup**, and the flight itself ran the whole corpus in under one GPU-hour against a
four-hour ceiling. No CPU packet preprocessing was started, and the legacy 26 GB `q4km` feature cache
was neither read nor written, so every encoder output in this number was produced on build
`04ccc72a`.

## 7. Deviations from the sealed arm, as preregistered

| # | deviation | effect |
|---|---|---|
| D1 | build `5d9dfcb58` → `04ccc72a` | measured, together with D2: +0.048 points on the ten |
| D2 | mmproj CPU → GPU | as D1; 5.47× throughput |
| D3 | `-c 81920 -np 8` → `-c 36864 -np 6` (slot 6,144, unchanged from the certified size) | none on request bytes |
| D4 | manifest scorers `["asr-wer","cost"]` → the four | the reason the paper number is on the verified path |
| D5 | no `LLAMA_MTMD_FEAT_CACHE_DIR` | no cross-build encoder reuse |
| D6 | `GGML_CUDA_DISABLE_GRAPHS=1` (recovery hardening) | none on request bytes |

D3 and D6 arrived with the one permitted recovery; Phase 5 of the preregistration carries the whole
story. Not one request byte differs from the sealed 2026-08-14 arm's protocol: same instruction, same
windowing, same evidence (none), same decoding params, same model files.

## 8. Defects found, and what was done about each

**1. The V1 flight died at 925 of 1,593 windows on a CUDA illegal memory access** (47 min 51 s in,
`ggml-cuda.cu:104` in `ggml_backend_cuda_synchronize`). The run had sat about 1 GB from the edge of a
24 GB card for its whole life. The one permitted recovery dropped `-np` 8 → 6 at an unchanged slot
size, freeing ~640 MiB of KV, and added `GGML_CUDA_DISABLE_GRAPHS=1` as hardening; V2 then flew the
full 1,593 windows at 22,720 MiB peak. Attribution between the two knobs was deliberately not
separated — the rules allow one recovery, and neither knob changes a request byte. 925 windows and
82,125 speech seconds were durably spent and no result was read from them.

**2. One missing corpus annotation refused all four scorers on a sealed 44-call run.** After V2
COMPLETED, `core.scorers.score_bundle` — which runs a manifest's whole scorer list — got
`asr-wer-whisper` and `asr-wer` through and then refused on `entity-wer`, because call `4320211`
references entity id `1057` and its sidecar never lists it. One id of 38,377, one tagged token of
55,294 (0.0026 % and 0.0018 %), and it made a completed flight unfinalizable.

`data.references.reference_entity_mentions` now splits two cases the old check conflated. An id the
sidecar **lists** but does not usably label is a corrupt annotation and **stays fatal**. An id the
sidecar **does not list at all** is an absent annotation and yields a mention typed `__UNTYPED__` —
never a real class, always counted, and visible as its own row with its own gold-mention count in
every `by_entity_type` table. The guarantee the old refusal protected (never silently *give* a
mention a class it does not have) is kept exactly; only the blast radius is gone.

Regression anchor, and it holds to the digit: re-scoring the sealed `SAEA-E-005B-N10-zero` outputs
after the change reproduces the 2026-09-04 audit's published entity numbers — **32.01 %** corpus
entity WER over **8,284** gold mentions — and no `__UNTYPED__` class appears among the ten, because
none of them references an absent id. Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-e21-full44-direct-baseline-v1/entity-annotation-defect/`.

**3. A self-inflicted one, recorded rather than hidden.** The first wire-check attempt ran all 68
contacts and then refused at finalize because `--ledger-cells` was absent, durably spending that
wire-check run id's registered audio seconds (`core/model/adapter.py` meters cumulatively across
attempts of a run id). It was retired and the check re-flown under a fresh wire-check run id rather
than by raising a budget.

## 9. Caveats that travel with this number

* **Whisper's own decoding heuristics move Earnings-21 by 1.1 points** (10.7 greedy to 9.63 with
  previous-text conditioning, Whisper Table 7). A ±3-point band around 9.71 is only about three times
  the reference literature's own protocol spread, and our margin (1.51) is inside that spread.
* **The Open ASR Leaderboard applies `merge_compounds=True`; we do not.** That works against us.
* **fstalign is never mixed in.** It is not installed and was not run.
* **This is a cross-system comparison, never a reproduction.** No Qwen-published Earnings-21 number
  exists; whisper-large-v3, large-v2, TRADE and FastConformer are third-party rows produced by other
  people's harnesses.
* **Segmentation.** Our 90-second fixed windows are neither Whisper's long-form decoding nor ConEC's
  sentence segmentation. The comparison is whole-file corpus WER against whole-file corpus WER, which
  is the closest available like-for-like, but the chunking is ours.
* **Discovery data.** The population is exposed discovery data and no knob was tuned on it. Nothing
  here is a superiority, generality or Stage-3 claim.

## 10. What this does and does not settle

It settles the conditionality. The 2026-09-04 audit's three caveats — 10 of 44 calls, `4346923`
excluded, the number produced out of band — are all gone: 44 of 44, `4346923` inside and costed at
+0.312, and the metric emitted by the verified scoring path from a manifest that declares it.

It does not settle the confound stack. The audit's own recommendation stands unchanged and is now the
obvious next move: **a self-run `whisper-large-v3` calibration anchor on our exact rows**, through the
same chunking and the same `core.scoring_batch` scorer. That is the only route that removes the
normalizer, aggregation, chunking, decoding-heuristic and quantization confounds together, the same
move the Audio2Tool carrier already made against its paper. It is not a frozen-core contact and needs
its own registration.

## 11. Per-call table, all 44 including `4346923`

`*` marks the ten calls of the sealed 2026-08-14 subset. Also in
`docs/checks/speech-aware-evidence-acquisition/2026-09-04-e21-full44-direct-baseline-v1/verdict/per-call-table.md`.

| call | company | sector | Hz | min | win | Whisper WER % | S | D | I | ref words | saea-v1 WER % | entity WER % | mentions |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4320211 | Monro Inc | Consumer Goods | 24000 | 54.8 | 37 | 7.16 | 286 | 104 | 231 | 8673 | 13.13 | 32.56 | 906 |
| 4330115* | Culp Inc | Industrial Goods | 24000 | 41.0 | 28 | 7.17 | 261 | 72 | 142 | 6628 | 11.15 | 33.05 | 596 |
| 4341191 | General Electric | Conglomerate | 24000 | 95.7 | 64 | 7.81 | 492 | 242 | 401 | 14541 | 11.34 | 22.95 | 1717 |
| 4344338 | Danaher Corp | Conglomerate | 44100 | 45.4 | 31 | 4.72 | 123 | 55 | 150 | 6946 | 7.97 | 26.31 | 631 |
| 4344866 | Spire Inc | Utilities | 24000 | 54.6 | 37 | 6.11 | 219 | 94 | 245 | 9130 | 9.16 | 22.32 | 869 |
| 4346818 | Ingersoll Rand | Industrial Goods | 11025 | 66.2 | 45 | 10.95 | 542 | 362 | 297 | 10968 | 15.31 | 33.08 | 1061 |
| **4346923** | Cementos Argos | Industrial Goods | 16000 | 78.5 | 53 | **18.94** | 917 | 426 | 579 | 10147 | 24.05 | 38.04 | 1062 |
| 4359732 | Kuehne Nagel International | Services | 44100 | 81.5 | 55 | 6.92 | 352 | 179 | 270 | 11573 | 11.82 | 24.39 | 1431 |
| 4359971 | Constellium | Industrial Goods | 24000 | 62.7 | 42 | 5.78 | 226 | 122 | 204 | 9554 | 10.82 | 28.55 | 1219 |
| 4360366 | Travelers Companies Inc | Financial | 24000 | 65.1 | 44 | 5.79 | 241 | 112 | 254 | 10491 | 9.71 | 26.03 | 1022 |
| 4360674 | Nextera Energy Inc | Utilities | 11025 | 59.9 | 40 | 8.18 | 361 | 122 | 298 | 9543 | 14.99 | 41.85 | 1257 |
| 4360717 | Fomento Economico Mexicano | Consumer Goods | 24000 | 75.2 | 51 | 8.40 | 440 | 308 | 253 | 11912 | 10.76 | 22.55 | 989 |
| 4361631 | Enagas | Utilities | 22050 | 73.5 | 50 | 7.26 | 283 | 155 | 209 | 8917 | 12.01 | 36.33 | 1057 |
| 4363614 | Banco Santander | Financial | 11025 | 93.1 | 63 | 14.84 | 778 | 339 | 861 | 13330 | 20.02 | 33.92 | 1026 |
| 4364366 | Mosaic Company | Basic Materials | 11025 | 58.4 | 39 | 10.18 | 447 | 103 | 291 | 8261 | 12.73 | 30.76 | 920 |
| 4365024* | Nextar Media Group | Services | 16000 | 72.1 | 49 | 6.91 | 348 | 172 | 283 | 11625 | 12.15 | 28.93 | 1469 |
| 4365948* | GCP Applied Technologies | Basic Materials | 22050 | 42.0 | 28 | 4.49 | 123 | 38 | 140 | 6704 | 10.39 | 30.45 | 936 |
| 4366302 | Healthcare Realty Trusts | Financial | 44100 | 59.9 | 40 | 5.80 | 257 | 90 | 234 | 10013 | 8.82 | 22.81 | 1109 |
| 4366429* | Dentsply Sironas XRay | Healthcare | 44100 | 66.8 | 45 | 6.55 | 270 | 216 | 254 | 11305 | 11.08 | 28.10 | 1153 |
| 4366522* | Aldeyra Therapeutics Inc | Healthcare | 22050 | 30.3 | 21 | 7.23 | 147 | 34 | 117 | 4123 | 11.65 | 41.43 | 519 |
| 4366893 | Earthstone Energy Inc | Basic Materials | 16000 | 39.4 | 27 | 7.67 | 221 | 93 | 176 | 6390 | 14.09 | 36.39 | 709 |
| 4367318 | AcelRX Pharmaceuticals Inc | Healthcare | 24000 | 28.7 | 20 | 7.02 | 157 | 43 | 103 | 4316 | 9.43 | 36.32 | 391 |
| 4367535 | Affimed | Healthcare | 24000 | 52.9 | 36 | 11.43 | 409 | 111 | 270 | 6914 | 17.51 | 43.47 | 651 |
| 4368670 | RWE Aktiengesellschaft | Utilities | 22050 | 70.4 | 47 | 10.10 | 482 | 320 | 329 | 11203 | 11.65 | 18.86 | 1092 |
| 4374910 | American Express Company | Financial | 24000 | 33.8 | 23 | 5.87 | 107 | 43 | 139 | 4921 | 7.89 | 35.96 | 317 |
| 4375653 | Illumina | Healthcare | 24000 | 57.9 | 39 | 7.99 | 337 | 100 | 320 | 9479 | 12.35 | 28.81 | 972 |
| 4382825 | Conocophillips | Basic Materials | 44100 | 63.3 | 43 | 10.63 | 463 | 263 | 412 | 10709 | 13.96 | 24.18 | 1274 |
| 4383161 | Pilgrims Pride Corp | Consumer Goods | 24000 | 56.3 | 38 | 8.24 | 407 | 124 | 204 | 8915 | 12.23 | 32.02 | 912 |
| 4384198 | New Home Company Inc | Industrial Goods | 44100 | 43.9 | 30 | 8.02 | 265 | 62 | 200 | 6568 | 13.84 | 36.31 | 661 |
| 4384683 | One Gas Inc | Basic Materials | 24000 | 24.6 | 17 | 6.64 | 83 | 32 | 125 | 3614 | 12.16 | 30.58 | 484 |
| 4384744 | Adtran Inc | Technology | 16000 | 54.5 | 37 | 9.22 | 354 | 155 | 243 | 8155 | 14.86 | 31.97 | 1001 |
| 4384964* | Eversource | Utilities | 24000 | 67.0 | 45 | 8.09 | 317 | 148 | 334 | 9879 | 11.41 | 25.89 | 931 |
| 4385072* | Sitime Corp | Technology | 24000 | 42.7 | 29 | 5.31 | 116 | 58 | 170 | 6480 | 11.38 | 35.28 | 669 |
| 4385388 | Yeti Holdings | Consumer Goods | 44100 | 72.4 | 49 | 6.25 | 267 | 83 | 360 | 11360 | 10.29 | 23.58 | 1319 |
| 4385939 | Hershey Company | Consumer Goods | 24000 | 50.8 | 34 | 5.02 | 183 | 93 | 181 | 9111 | 7.03 | 21.89 | 804 |
| 4386541 | Cumulus Media Inc | Services | 16000 | 18.3 | 13 | 6.36 | 65 | 34 | 74 | 2722 | 12.08 | 31.32 | 364 |
| 4387332 | Zagg Inc | Services | 24000 | 21.8 | 15 | 6.28 | 125 | 52 | 76 | 4030 | 12.03 | 34.19 | 430 |
| 4387383* | Clipper Realty Inc | Financial | 22050 | 36.0 | 24 | 6.70 | 124 | 41 | 81 | 3672 | 12.64 | 36.96 | 395 |
| 4387865 | Indentiv Inc | Technology | 11025 | 36.0 | 25 | 8.77 | 236 | 118 | 165 | 5921 | 16.81 | 44.26 | 906 |
| 4389907* | Pheonix New Media Ltd | Technology | 24000 | 34.3 | 23 | 13.14 | 235 | 40 | 243 | 3942 | 19.27 | 42.93 | 396 |
| 4392809 | Lands End Inc | Services | 24000 | 24.0 | 16 | 4.19 | 60 | 32 | 79 | 4079 | 7.92 | 22.62 | 336 |
| 4394084 | Innovative Solutions and Support Inc | Technology | 16000 | 29.3 | 20 | 12.16 | 214 | 85 | 143 | 3636 | 18.77 | 49.35 | 460 |
| 4397800 | Rev Group Inc | Conglomerate | 24000 | 46.2 | 31 | 7.84 | 290 | 107 | 228 | 7972 | 10.99 | 27.25 | 723 |
| 4397829* | Bed Bath and Beyond Inc | Conglomerate | 24000 | 74.5 | 50 | 8.07 | 468 | 119 | 332 | 11393 | 12.37 | 31.56 | 1220 |

**All 44: corpus Whisper-normalized WER 8.200 %** (S 13,098 / D 5,701 / I 10,700 over 359,765
reference words); mean of per-call 8.004 %.
