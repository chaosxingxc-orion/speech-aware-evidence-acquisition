# MF-7b — the SLURP retrieval-key audit, GPU part: omni-embedding speech-to-text matching

Preregistration: `docs/readiness/2026-09-06-slurp-retrieval-key-audit-v2-preregistration.md`,
committed before the first contact. Predecessor: `2026-09-06-slurp-retrieval-key-audit-v1.md`
(MF-7, CPU part). Receipts:
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-retrieval-key-audit-v2/`.
Exposure rows `SAEA-SLURP-MF7B-LCO-EMBEDDING-V1`, `SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1` (tool
contacts, GPU) and `SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V2` (the model-free read). **Zero
frozen-core contacts.**

## Verdict

**The gate is NOT cleared. Neighbour retrieval on SLURP intent is CLOSED, and is re-scoped to the
slot side (KU-S3) and to Audio2Tool (KU-A1) exactly as preregistered.** No
`phase_supply.evidence.query_source` block is produced; the KU-S1 fragment keeps its 64-`f`
placeholder and stays NOT FLYABLE.

Decision k = 5, decision population NEW500 (n = 500), comparator the **re-locked** closed-list arm
plus `slurp-legal-label-projection-v2` scored through `slurp-slu-official-projected-v2` — intent
**75.20** on NEW500, so **376 right rows to harm and 124 wrong rows to save**.

| set | role | net corrective NEW500 | CI90 | echo | verdict |
|---|---|---|---|---|---|
| `q-speech-nemotron-fused` | candidate | **+0.60 pp** (50 saves / 47 harms) | [−2.40, +3.60] | 74.75 | **winner, and it fails BOTH halves of the gate** |
| `q-speech-nemotron` | candidate | −3.40 pp (56 / 73) | [−7.00, +0.20] | 63.53 | runner-up, negative |
| `q-speech-glap` | candidate | −34.60 pp (25 / 198) | [−38.60, −30.60] | 36.07 | harmful |
| `q-speech-lco-fused` | candidate | −59.00 pp (5 / 300) | [−62.40, −55.40] | 16.63 | catastrophic |
| `q-speech-lco` | candidate | −71.20 pp (1 / 357) | [−74.20, −68.00] | 4.01 | catastrophic |
| `q-speech-nemotron+state` | candidate | +0.60 pp (14 / 11) | [−1.00, +2.20] | **96.19** | **DEGENERATE** (clause 2) |
| `q-speech-glap+state` | candidate | +0.40 pp (16 / 14) | [−1.20, +2.00] | **96.19** | **DEGENERATE** |
| `q-speech-lco+state` | candidate | −1.00 pp (13 / 18) | [−2.80, +0.60] | **96.19** | **DEGENERATE** |
| `q-gold-text` | diagnostic | +11.00 pp (79 / 24) | [+8.00, +14.20] | 72.55 | text ceiling, never eligible |
| `q-draft` | diagnostic | −11.40 pp (38 / 95) | [−14.60, −8.20] | 71.34 | legacy signal, never eligible |

The gate needed **≥ 2.00 pp AND a CI90 lower bound above zero**. The winner reaches +0.60 with a
lower bound of −2.40: it fails on the point estimate and on the interval. **Cross-modal loss:
10.40 pp** (`q-gold-text` +11.00 minus the winner's +0.60).

## 1. The finding that matters more than the verdict

**A real omni embedder very nearly closes the modality gap MF-7 measured; it is the comparator that
has moved out of reach.**

| set | intent recall@5 | vote acc@5 | filler recall@5 |
|---|---|---|---|
| `q-gold-text` (transcript query — the ceiling) | **93.80** | **86.20** | **64.02** |
| `q-speech-nemotron-fused` | **87.40** | 75.80 | 42.85 |
| `q-speech-nemotron` | 83.20 | 71.80 | 43.46 |
| `q-speech-glap` (MF-7's encoder) | 63.00 | 40.60 | 35.28 |
| `q-speech-lco` | 12.40 | 4.00 | 1.80 |

Against GLAP, the Nemotron speech query is **+35.20 pp net corrective power on NEW500, CI90
[+31.20, +39.20], p 1.4e-36** — the largest paired delta in this audit. MF-7's headline was "the
gold intent usually IS somewhere in the ten neighbours and the ranking is too weak for a vote to
find it"; on Nemotron the ranking is no longer too weak. Recall@5 sits **6.40 pp** under the
transcript ceiling and vote accuracy **10.40 pp** under it, where GLAP sat 30.80 and 45.60 under.

And yet the corrective power is +0.60. The reason is arithmetic and worth stating plainly: **the
comparator is 75.20 and the best speech vote is 75.80.** A majority vote that is exactly as
accurate as the arm it is meant to repair saves about as many rows as it breaks — 50 saves against
47 harms. The mechanism is not absent; it is not *better than what it would replace*.

Two consequences follow, and neither is a licence to fly anything.

* **The 2026-09-06 re-lock absorbed most of the headroom this audit was hunting.** MF-7's winner
  `q-speech-glap+state` scored +2.40 pp against the unprojected mask and scores **+0.40 pp**
  against the re-locked one. The projection's 17 free saves are 17 rows a retrieval plane no longer
  gets to claim. Any future SLURP intent mechanism has to beat 73.10 pooled / 75.20 NEW500, and a
  neighbour vote at 75.80 is not a mechanism, it is a tie.
* **The slot side keeps its signal.** `q-speech-nemotron-fused`'s filler recall@5 is 42.85 against
  `q-draft`'s 31.47 — paired **+7.90 CI90 [+5.37, +10.43]** — and 43.46 for speech alone. That is
  the reading clause 5 of the preregistration re-scopes to, and it is consistent with KC-S1b's
  admitted +8.55 SLU-F1 slot mechanism.

## 2. Each tower is healthy; the loss is between them

`key-space-coherence.json`, zero contacts. "Nearest other" = does a row's nearest *other* row in
the same space carry the same gold intent?

| encoder | text key space (11,514 TRAIN texts) | speech query space (1,000 DEV recordings) | TRAIN text → its own label (60 labels, chance 1.67) |
|---|---|---|---|
| `omni-embed-nemotron-3b` | **81.47** (mean cos +0.8692) | **59.60** (mean cos +0.1772) | **38.35** |
| `lco-embedding-omni-3b` | 70.63 (+0.5752) | 20.70 (+0.8959) | 12.35 |
| `glap` | 63.83 (+0.5963) | 16.90 (+0.4882) | — |

Every text tower works. Nemotron's *speech* tower also works — two recordings of the same intent
are nearest neighbours 59.60 % of the time — while GLAP's and LCO's barely do. LCO's speech
vectors are mutually similar at mean cosine 0.896: they occupy a narrow cone that carries little
intent structure, which is exactly what a 4.00 vote accuracy looks like from the inside.

**Cross-modal separation** (`cosine-separation.json`, matched = the key's TRAIN intent equals the
row's gold intent; pooled 1,000 × 11,514):

| set | matched mean | unmatched mean | delta | standardised |
|---|---|---|---|---|
| `q-speech-nemotron-fused` | +0.3271 | +0.2770 | **+0.0501** | **+1.084** |
| `q-speech-nemotron` | +0.2715 | +0.2260 | +0.0455 | +0.718 |
| `q-speech-glap` | −0.0294 | −0.0619 | +0.0325 | +0.440 |
| `q-speech-lco-fused` | +0.0852 | +0.0695 | +0.0157 | +0.396 |
| `q-speech-lco` | +0.0644 | +0.0572 | +0.0072 | +0.183 |

The standardised separation orders the encoders exactly as the vote accuracy does, which is the
point of reporting it: a set that cannot vote also cannot separate, so the failure is a
representation failure and not a consumer-side artefact.

## 3. The `+state` sets degenerated exactly as predicted, before the run

All three rank-level `+state` sets echo the draft's own label on **96.19 %** of the 499 parsed
NEW500 rows — the same figure for GLAP, LCO and Nemotron, to the digit, because the fusion's
dominance margin at the registered weights (`w_cos` 0.5 / `w_prior` 0.3 / `w_agree` 0.2) is 0.8 raw
cosine and no SLURP cosine comes near it. The preregistration's clause 2 named 90 % as the
degeneracy line and section 4's closing paragraph said this would happen *from the arithmetic, not
from a v2 number*. It did. Those three sets are reported and cannot win.

**Input-level fusion is the interesting one, and it is not degenerate.** `q-speech-nemotron-fused`
echoes 74.75 % — well below the line — and it is the only fusion that changes what is retrieved
rather than what is ranked: recall@5 rises 83.20 → 87.40 and vote 71.80 → 75.80 over speech alone,
paired **+4.00 pp net CI90 [+1.00, +7.20]**. Fusing the agent's own state *inside the encoder*
genuinely helps; fusing it in the ranker just returns the state.

## 4. LCO under its own documented protocol, and the limitation that carries

`q-speech-lco` is the worst set in this audit: recall@5 12.40, vote 4.00, net −71.20 pp. Its text
tower is fine (70.63), so this is entirely the audio path: audio-to-text cosines sit at mean 0.057
with a matched/unmatched delta of +0.0072, i.e. the audio vectors occupy a cone nearly orthogonal
to the text vectors.

**What was run is the model card's own documented protocol**, byte for byte: `llama-server
--embedding --pooling last` with `{"content": [{"prompt_string": <media marker>,
"multimodal_data": [<base64 wav>]}]}` for audio and `{"content": [<text>]}` for text, on the pinned
featcache build `04ccc72a`, with the server's randomised media marker verified against live
`/props` before the first embedding. The GGUF and mmproj sha256 match the umbrella lock. The jitter
pair is bit-exact.

**The named limitation, with the experiment that would settle it.** llama.cpp's `/embedding`
endpoint tokenises `prompt_string` as given and applies no chat template. LCO-Embedding-Omni is a
Qwen2.5-Omni Thinker with **last-token** pooling, so under this protocol the pooled vector for an
audio query is the hidden state of the final *audio* token, while for a text key it is the final
*text* token — two structurally different positions. Omni-Embed-Nemotron, whose result is far
better, went through its own shipped `sentence_transformers.jinja` wrapper on both sides. **A
template-wrapped LCO pass was NOT run**: it is a different query set from the ones the
preregistration fixed, it would be chosen after seeing a bad number, and its outcome cannot change
this verdict — Nemotron already answers the scientific question of whether an omni embedder can
close the gap. If a later owner decision wants it, the experiment is exactly: re-embed the 11,514
TRAIN texts and the 1,000 recordings with `prompt_string` set to the Qwen2.5-Omni chat wrapper on
both sides, under its own registered row, and compare against this row's numbers. **Until then the
LCO result is licensed as "LCO-Embedding-Omni-3B-Q8_0 through its published llama.cpp embedding
protocol", not as "LCO-Embedding-Omni".**

## 5. The label-key space — reported, never deciding (clause 6)

Keys are the 60 legal `(scenario, action)` pairs of the closed-list inventory under the
preregistered rule `saea-mf7b-label-text-v1` (`f"{scenario} {action}"`, underscores to spaces,
lower-case; no gloss written by anyone). A label key carries no slots, so filler recall is `null`
here rather than a misleading zero.

| set | intent recall@5 | vote acc@5 | net NEW500 | CI90 | echo |
|---|---|---|---|---|---|
| `q-speech-nemotron+state` | 86.00 | 75.60 | +0.40 | [−1.20, +2.00] | 96.19 (degenerate) |
| `q-speech-nemotron` | 68.00 | 39.00 | −36.20 | [−40.01, −32.39] | 39.08 |
| `q-speech-nemotron-fused` | 66.80 | 33.40 | −41.80 | [−45.00, −38.60] | 40.68 |
| `q-speech-lco+state` | 74.60 | 74.20 | −1.00 | [−2.80, +0.60] | 96.19 (degenerate) |
| `q-speech-lco-fused` | 21.20 | 5.00 | −70.20 | [−73.20, −67.00] | 8.62 |
| `q-speech-lco` | 8.60 | 0.80 | −74.40 | [−77.40, −71.40] | 2.40 |

Matching speech against **label text** is strictly worse than matching it against **TRAIN utterance
text** for every non-degenerate set — Nemotron drops from 71.80 to 39.00 vote accuracy. The 60
label strings are short, abstract and mutually similar; an utterance key carries the phrasing a
speaker actually uses. The label space's *separation* is not the problem (`q-speech-nemotron-fused`
scores its highest standardised separation there, +1.554); the problem is that 60 keys give a
top-5 vote almost no room to be selective. This closes the label-space branch as a *retrieval* key
and says nothing about labels as a decode constraint, which is what the projection already is.

## 6. The full table at k = 5, NEW500 / OLD500 / pooled

| set | pop | recall@5 | vote@5 | saves | harms | net pp | filler@5 | echo |
|---|---|---|---|---|---|---|---|---|
| `q-draft` | NEW500 | 74.60 | 63.80 | 38 | 95 | −11.40 | 31.47 | 71.34 |
| | OLD500 | 69.40 | 59.40 | 41 | 99 | −11.60 | 25.76 | 67.13 |
| | pooled | 72.00 | 61.60 | 79 | 194 | −11.50 | 28.73 | 69.24 |
| `q-gold-text` | NEW500 | **93.80** | **86.20** | 79 | 24 | **+11.00** | **64.02** | 72.55 |
| | OLD500 | 92.20 | 82.80 | 87 | 28 | +11.80 | 59.11 | 68.54 |
| | pooled | 93.00 | 84.50 | 166 | 52 | +11.40 | 61.67 | 70.54 |
| `q-speech-glap` | NEW500 | 63.00 | 40.60 | 25 | 198 | −34.60 | 35.28 | 36.07 |
| | OLD500 | 64.40 | 42.40 | 37 | 180 | −28.60 | 34.32 | 35.87 |
| | pooled | 63.70 | 41.50 | 62 | 378 | −31.60 | 34.82 | 35.97 |
| `q-speech-glap+state` | NEW500 | 77.60 | 75.60 | 16 | 14 | +0.40 | 40.90 | 96.19 |
| | OLD500 | 73.60 | 72.60 | 19 | 11 | +1.60 | 39.11 | 96.79 |
| | pooled | 75.60 | 74.10 | 35 | 25 | +1.00 | 40.04 | 96.49 |
| `q-speech-lco` | NEW500 | 12.40 | 4.00 | 1 | 357 | −71.20 | 1.80 | 4.01 |
| | OLD500 | 12.80 | 4.20 | 4 | 338 | −66.80 | 1.61 | 4.21 |
| | pooled | 12.60 | 4.10 | 5 | 695 | −69.00 | 1.71 | 4.11 |
| `q-speech-lco+state` | NEW500 | 75.20 | 74.20 | 13 | 18 | −1.00 | 23.18 | 96.19 |
| | OLD500 | 71.60 | 71.00 | 14 | 14 | +0.00 | 20.96 | 96.79 |
| | pooled | 73.40 | 72.60 | 27 | 32 | −0.50 | 22.12 | 96.49 |
| `q-speech-lco-fused` | NEW500 | 27.60 | 16.20 | 5 | 300 | −59.00 | 8.00 | 16.63 |
| | OLD500 | 30.20 | 15.80 | 13 | 289 | −55.20 | 10.91 | 16.03 |
| | pooled | 28.90 | 16.00 | 18 | 589 | −57.10 | 9.40 | 16.33 |
| `q-speech-nemotron` | NEW500 | 83.20 | 71.80 | 56 | 73 | −3.40 | 43.46 | 63.53 |
| | OLD500 | 84.40 | 69.40 | 71 | 79 | −1.60 | 40.21 | 58.72 |
| | pooled | 83.80 | 70.60 | 127 | 152 | −2.50 | 41.90 | 61.12 |
| `q-speech-nemotron+state` | NEW500 | 77.80 | 75.80 | 14 | 11 | +0.60 | 40.34 | 96.19 |
| | OLD500 | 75.00 | 73.60 | 21 | 8 | +2.60 | 38.49 | 96.79 |
| | pooled | 76.40 | 74.70 | 35 | 19 | +1.60 | 39.45 | 96.49 |
| **`q-speech-nemotron-fused`** | **NEW500** | **87.40** | **75.80** | **50** | **47** | **+0.60** | **42.85** | **74.75** |
| | OLD500 | 85.20 | 74.00 | 63 | 48 | +3.00 | 41.09 | 73.15 |
| | pooled | 86.30 | 74.90 | 113 | 95 | +1.80 | 42.01 | 73.95 |

k = 1 and k = 10 move nothing that matters: the winner's net is −1.40 / +0.60 / +1.60 at k = 1 / 5
/ 10 on NEW500, and `q-speech-nemotron`'s is −4.80 / −3.40 / −4.40. `q-speech-nemotron-fused`
reaches **recall@10 90.20** against the ceiling's 95.40 — the neighbours are there; the vote is
what cannot use them.

**OLD500 is friendlier and does not change anything.** The winner scores +3.00 on the prior-exposed
half against +0.60 on the unexposed one, which is the usual direction on this roster and is exactly
why NEW500 is the decision population. Pooled would be +1.80, still under the gate.

## 7. Per stratum, NEW500, k = 5 (net corrective pp)

| scenario | n | nemo-fused | nemo | gold-text | glap | nemo+state | nemo-fused recall@5 |
|---|---|---|---|---|---|---|---|
| `alarm` | 30 | +3.33 | −3.33 | −3.33 | −46.67 | +3.33 | 93.33 |
| `audio` | 2 | −50.00 | −50.00 | +0.00 | −50.00 | +0.00 | 100.00 |
| `calendar` | 33 | +15.15 | +6.06 | +21.21 | −24.24 | +3.03 | 90.91 |
| `cooking` | 9 | +22.22 | +22.22 | +11.11 | −22.22 | +11.11 | 77.78 |
| `datetime` | 33 | +9.09 | −6.06 | +12.12 | −21.21 | +3.03 | 96.97 |
| `email` | 33 | −9.09 | −3.03 | +9.09 | −51.52 | +3.03 | 93.94 |
| `general` | 33 | −9.09 | +0.00 | +6.06 | −24.24 | −3.03 | 60.61 |
| `iot` | 33 | −9.09 | −12.12 | +3.03 | −36.36 | +0.00 | 96.97 |
| `lists` | 32 | −12.50 | −6.25 | +3.12 | −40.62 | +0.00 | 87.50 |
| `music` | 23 | −30.43 | −30.43 | −17.39 | −43.48 | +0.00 | 65.22 |
| `news` | 32 | +0.00 | −6.25 | +9.38 | −28.12 | +0.00 | 84.38 |
| `play` | 32 | +25.00 | +21.88 | +46.88 | −3.12 | −12.50 | 90.62 |
| `qa` | 32 | +12.50 | +6.25 | +18.75 | −28.12 | +9.38 | 84.38 |
| `recommendation` | 32 | +0.00 | −6.25 | +9.38 | −59.38 | −6.25 | 90.62 |
| `social` | 33 | −6.06 | −9.09 | +12.12 | −39.39 | −3.03 | 84.85 |
| `takeaway` | 12 | −16.67 | −33.33 | +8.33 | −66.67 | −8.33 | 83.33 |
| `transport` | 33 | +18.18 | +6.06 | +24.24 | −18.18 | +12.12 | 93.94 |
| `weather` | 33 | −3.03 | −9.09 | +3.03 | −48.48 | +0.00 | 93.94 |

The winner is genuinely mixed, not uniformly flat: it gains 8 strata and loses 7, its best is
`play` (+25.00) and `cooking` (+22.22) and its worst is `music` (−30.43) — and `music` is the one
stratum where even the transcript ceiling is negative (−17.39), so it is a labelling difficulty
rather than an encoder failure. No stratum carries the verdict, and no stratum rescues it.
`audio` (n = 2) is shown only for completeness.

## 8. Cost, and the accounting

| pass | contacts | forwards | GPU-h | audio throughput | text throughput | jitter |
|---|---|---|---|---|---|---|
| `SAEA-SLURP-MF7B-LCO-EMBEDDING-V1` | 13,575 (ceiling 13,600) | 2,363 HTTP requests | **0.2565** | 2.670 clips/s, **7.70× realtime** | 74.15 texts/s (batch 32) | **bit-exact**, max abs delta 0.0 |
| `SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1` | 13,575 + 7 dry-run (ceiling 13,600) | 2,725 | **0.1101** | 6.493 clips/s, **18.73× realtime** | 155.03 texts/s (batch 16) | **bit-exact**, max abs delta 0.0 |
| `SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V2` | 0 | 0 | 0.0 | — | — | — |

**0 frozen-core contacts** in all three; 0 paid API spend. Both passes traversed the roster's own
2,884.7937 speech seconds twice (5,769.5874 s each). Both estimates were under the preregistered
≤ 1.5 GPU-h per embedder; the two together cost **0.367 GPU-h**. Every L2 norm is 1.0 to seven
decimals. Nemotron is 2.4× faster than LCO on audio and 2.1× on text despite being a bf16 3B in
`transformers` against a Q8_0 GGUF in llama.cpp — the LCO audio path pays for one HTTP request and
one mmproj encode per clip.

The 7 extra Nemotron contacts are a 2-row loader dry run (`--limit 2 --no-write`) that wrote
nothing and is recorded here and in the ledger rather than being quietly absorbed.

## 9. What this closes, and what it hands on

* **CLOSED: neighbour retrieval on SLURP intent.** Three encoders, six speech-containing query
  sets, two key spaces, and the best of them ties the comparator. No KU-S1-prime cell is licensed;
  the KU-S1 v2 fragment's `phase_supply.evidence.query_source.sha256` stays the 64-`f` placeholder
  and its `embedded_signal` stays unfixed, so `rails.phase_supply.load_sealed_vectors` continues to
  refuse it at preflight. **That refusal is now the correct state, not a missing enabler.**
* **Handed to KU-S3 (the slot side).** Filler recall@5 is 42.85 for the winner against `q-draft`'s
  31.47 (+7.90 CI90 [+5.37, +10.43]) and 64.02 for the transcript ceiling. The slot side is where
  a speech-keyed neighbour still carries information the arm does not already have, and KC-S1b's
  admitted +8.55 SLU-F1 is the base to build it on.
* **Handed to KU-A1 (Audio2Tool).** Both embedders are now built, receipted and cheap
  (0.11–0.26 GPU-h per full carrier pass), and MF-6 should be measured with them. Audio2Tool's
  comparator is not a 75-point closed-list arm, so a 75-point retriever is not automatically a tie
  there.
* **A methodological result for every future retrieval cell on this carrier:** report the echo rate
  AND the standardised cross-modal separation beside the vote. Three of the ten sets here reach
  96 % echo, and the separation ordered the encoders correctly before any bootstrap was run.

## 10. Limits carried

* The `test` split was never named, loaded, scored or embedded. **No devel sentence text was read
  in this part at all** — `q-gold-text` was carried forward from MF-7's sealed vectors, so the
  ceiling is inherited rather than recomputed.
* DEV-1000 is prior-exposed as a whole; NEW500 is the only unexposed half and is the decision
  population. No new evaluation surface opened.
* The audit measures what neighbours *contain* under a MAJORITY-VOTE consumer, not what a frozen
  core would *do* with them. `q-speech-nemotron-fused` has recall@10 of 90.20 against a vote of
  76.80: a consumer that supplied the neighbours as evidence, weighted them by similarity, or
  abstained below a threshold could do better on the same neighbours. What is ruled out is the
  vote, not every possible use — and that caveat is now much heavier than it was in MF-7, because
  the recall is high and it is only the vote that is flat.
* The LCO result is licensed only for its published llama.cpp embedding protocol (section 4).
* Two encoders were measured on the GPU. "An omni-embedding speech query cannot correct SLURP
  intent by neighbour vote" is licensed for GLAP, LCO-Embedding-Omni-3B and Omni-Embed-Nemotron-3B
  against the re-locked comparator, on this carrier, at k ≤ 10.
* Nemotron's **speech-to-speech** structure is strong (59.60 nearest-neighbour intent agreement)
  and was NOT exploited: the owner's 2026-09-06 restriction scopes this part to speech-to-text
  matching, and a speech-keyed speech corpus is a different mechanism with a different cost.
  That number is recorded so a later decision can price it, not proposed as a next step.
* No admission, promotion, superiority, generality or Stage-3 claim follows from this note.
