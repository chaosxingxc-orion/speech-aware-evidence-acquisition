# MF-7 — the SLURP retrieval-key audit (2026-09-06)

Prerequisite MF-7, owner GO 2026-09-06, amended the same day by the owner rule that **the
retrieval query must contain the speech signal**. Profile `model-free-check`; **zero frozen-core
contacts, zero GPU**. Exposure rows `SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V1` (the reads) and
`SAEA-SLURP-MF7-EMBEDDING-CPU-V1` (the CPU encoder passes), both registered before the first read.
Receipts: `docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-retrieval-key-audit/`.

**Preregistration, stated exactly.** Sections 1–4 — the protocol, the candidate/diagnostic split,
the closed-form prediction about the fusion, and the decision table — were written and **committed
before the audit was run** (commit `preregister: MF-7 asks which query signal corrects SLURP
intent`). Section 5 was appended afterwards. Section 6 was drafted before the run and then
**revised after it**, to replace its argued-from-source claim about LCO with the measurements from
the CPU loader probe; none of section 6 feeds the decision table.

## 1. The question

Every SLURP retrieval cell so far has used the embedding of the frozen core's **own draft answer**
as the query, against the 11,514 TRAIN utterance texts as keys
(`rails.knowledge_provider.KbFacetProvider`, ranked by `saea-rank-wcos-prior-agree-v1`). KU-S1c
established that a second look at the same audio buys +0.30 pp intent, inside noise, and that
"contacts are not the lever on SLURP; constructed knowledge is". Before another consumption cell is
flown, the audit asks the prior question:

> **Which query signal, paired with TRAIN utterance texts as keys, retrieves neighbours that could
> CORRECT the closed-list baseline?**

Measured on DEV-1000, already consumed by the DEV ladder, so no new evaluation surface opens.
Reported on the unexposed NEW500 and the prior-exposed OLD500 separately, pooled 1,000 beside them.

## 2. What is a candidate and what is only a diagnostic

The owner rule of 2026-09-06 is binding and is encoded in the analysis module, not merely reported
by it (`analysis.slurp_retrieval_key_audit.DIAGNOSTIC_ONLY`, enforced in `decision()`):

| query set | contains speech | role | why |
|---|---|---|---|
| `q-draft` | no | **diagnostic only** | the lock's LEGACY signal; the query IS the model's own draft answer. Its point is the ECHO RATE — how much of the "retrieved evidence" is the model's own label coming back. |
| `q-gold-text` | no | **diagnostic only** | the query IS the gold sentence: the UPPER BOUND of any text key. Its point is to price the cross-modal loss and to say whether ANY text key is worth pursuing. |
| `q-speech-glap` | yes | candidate | DEV recordings through GLAP's audio encoder; keys = TRAIN texts through GLAP's text encoder. Run here, on CPU. |
| `q-speech-glap+state` | yes | candidate | the same speech query fused at RANK level with the agent's own intermediate state (the sealed draft's intent) under the registered ranker. Run here, on CPU. |
| `q-speech-lco`, `+state`, `-fused` | yes | candidate | LCO-Embedding-Omni-3B: speech alone, rank-level fusion, and input-level fusion (audio and the draft text as ONE multimodal input). **Prepared, not run** (section 6). |
| `q-speech-nemotron`, `+state`, `-fused` | yes | candidate | Omni-Embed-Nemotron-3B, same three shapes. **Prepared, not run** (section 6). |

Neither text-only set can win, however good its numbers are. A text-only query presupposes a
transcript the control plane does not have at retrieval time.

## 3. Protocol

**Keys.** The 11,514 TRAIN content facets of snapshot
`e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57` — one per TRAIN utterance, the
utterance text as the key representation — each carrying its TRAIN gold intent (`scenario_action`)
and its gold `{type, filler}` slots. TRAIN is construction data and is readable. For `q-draft` and
`q-gold-text` the key vectors are the **sealed** `vectors-content-facets.npz`
(sha256 `0bcb955a3a0ab84880f0d039ae702e77d1247ed23c3b8cecb468cbb1e0221c72`, re-verified before use,
zero new contacts). For a speech set the keys are re-embedded by that set's OWN model, because a
query may only be compared against keys embedded by the same encoder.

**Queries.** The DEV-1000 roster (split identity `9fb44e3384b8ad8e0d8f825b88eb0a3051c218b699975051d8a0481aabc0243b`),
1,000 rows, NEW500 the decision population. `q-draft` is the sealed KU-S1c **phase-1 draft response
text** per row (run `SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1`, attempt
`attempt-20260906T042946Z-44720f`); the KU-S1 prep agent left only `facet-vectors.jsonl` under
`SPEECHRL_DATA_DIR/vectors/slurp-ku-s1/` — no `query-vectors.jsonl` and no query receipt — so the
draft texts were embedded here rather than reused. `q-gold-text` is the devel sentence text, read
**only** to compute embeddings under the audit row; it is written to no receipt, document, table
cell or log line. `q-speech-glap` is the recording waveform at 16 kHz.

**Baseline mask.** The per-row `scenario_action_exact` of the sealed closed-list direct baseline
`SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` (attempt `attempt-20260905T060424Z-2c5596`), official
`evaluate.py` scorer at pinned commit `8eb1654…311f1`.

**Neighbours.** Cosine top-k over the complete key set, k ∈ {1, 5, 10}, ties broken by ascending
facet id — the lock's own tie-break.

**Metrics** (per query set, per k, per population NEW500 / OLD500 / pooled, and per gold scenario):

1. **intent recall@k** — the gold intent appears among the k neighbours' TRAIN intents.
2. **vote accuracy@k** — the neighbours' MAJORITY intent equals gold, ties broken by best rank.
3. **corrective power** — among rows the sealed baseline got WRONG on intent, the share the
   majority would have SAVED; among rows it got RIGHT, the share it would have HARMED;
   net = saves − harms, in rows and in pp of the population.
4. **filler recall@k** — the share of the row's gold `{type, filler}` slots present verbatim among
   the neighbours' TRAIN slots. Both sides come through `data.slurp`'s official gold-side join
   (`" ".join(surface.lower())`), so "verbatim" is the official comparison with no second
   normalizer. Reported over the rows that HAVE at least one gold slot.
5. **echo rate** — the majority equals the sealed draft's own label. Reported for every set.

**The `+state` fusion.** Rank-level, under the registered ranker `saea-rank-wcos-prior-agree-v1`
with its registered weights and **no new knob**: `w_cos·max_cosine + w_prior·max_prior +
w_agree·agreement`, `w_cos = 0.5, w_prior = 0.3, w_agree = 0.2` read from
`configs/policy/kb-policy-v1.json`. The speech cosine is the content dimension; the PRIOR dimension
is the agent's own intermediate state — a key is recalled on it iff its TRAIN intent equals the
sealed draft's intent, mass 1.0 — and `agreement` is the lock's own fraction-of-recalled-dimensions
term. Two deliberate deviations from `rails.kb_policy`, both because this audits the KEY side
rather than replaying the locked cell: no per-dimension truncation before the union (an audit needs
a complete ranking), and the prior is the draft's intent rather than the snapshot's 60 TRAIN intent
priors.

**A closed-form property of that fusion, stated before the run.** A draft-agreeing key scores
`w_cos·c + w_prior + w_agree`; a disagreeing one scores `w_cos·c + w_agree/2`. The raw-cosine
advantage a disagreeing key needs is `(w_prior + w_agree/2)/w_cos = **0.8**`. Since SLURP cosines
live far inside that span, rank-level fusion at the registered weights is very close to a HARD
restriction to the draft's intent, and its vote is the draft's label whenever k such keys exist
(~190 TRAIN utterances per intent, so always). This is a property of the registered ranker, not a
choice made in the audit: `analysis.slurp_retrieval_key_audit.fusion_dominance_margin` computes it
and the receipt carries it. The prediction is therefore that `+state`'s echo rate is ~100 % and its
corrective power equals the draft label's own corrective power against the closed-list baseline.

**Statistics.** Stratified paired bootstrap, 10,000 replicates, seed 20260903, strata = gold
scenario, CI90, through this repository's single resampler `analysis.paired.paired_contrast` — the
same one every SLURP verdict uses. A single set's own level gets a CI by contrasting it against an
all-zero table, so there is exactly one bootstrap implementation in the repository.

## 4. The preregistered decision table (owner rule 2026-09-06, clause 3)

1. **KU-S1 flies with the speech-containing query set that has the highest net corrective power on
   NEW500.** The CI90 against the runner-up is reported. Ties go to the simpler signal: speech
   alone before speech+state, fewer models before more.
2. **If the best speech-containing set's net corrective power is below 2 pp of rows on NEW500,
   retrieval-by-neighbours on SLURP intent is CLOSED** and this note says so.
3. **The gap to `q-gold-text` is reported as the cross-modal loss.** `q-gold-text` also answers the
   separate question of whether ANY text key is worth pursuing: if even the gold-sentence query's
   net corrective power is under 2 pp, no text key can carry this mechanism.
4. **Filler recall@5 is reported for every set but does not gate.** It is the slot-side reading, and
   the slot side already has an admitted mechanism (KC-S1b's TRAIN slot schema, +8.55 SLU-F1).
5. `q-draft` and `q-gold-text` are never eligible to win, whatever their numbers.

No admission, promotion, superiority, generality or Stage-3 claim follows from this note. Its only
product is a gate on whether a KU-S1-prime retrieval cell is worth flying at all.

## 5. Results

**Verdict in one line: the gate is cleared on the point estimate by the single degenerate set, and
the mechanism that clears it is not retrieval. A speech query on this carrier, with GLAP as the
encoder, is not a viable retrieval key — and the text ceiling shows the loss is cross-modal, not
inherent to neighbour voting.**

Decision k = 5, decision population NEW500 (unexposed, n = 500, sealed-baseline intent accuracy
73.20 — 134 wrong rows and 366 right rows to save or harm).

### 5.1 The decision table applied

| query set | role | net corrective NEW500 | CI90 | verdict |
|---|---|---|---|---|
| `q-speech-glap+state` | candidate | **+2.40 pp** (21 saves / 9 harms) | [+0.80, +4.20] | winner; clears the 2 pp gate on the point estimate only |
| `q-speech-glap` | candidate | **−32.60 pp** (26 saves / 189 harms) | [−36.60, −28.60] | catastrophically harmful |
| `q-gold-text` | diagnostic (text ceiling) | +13.00 pp (88 / 23) | [+9.80, +16.20] | not eligible |
| `q-draft` | diagnostic (legacy signal) | −9.40 pp (42 / 89) | [−12.60, −6.20] | not eligible |

`q-speech-glap+state` wins among the speech-containing sets and its point estimate clears the
preregistered 2 pp gate. **Its CI90 lower bound is +0.80, which does not exclude values under the
gate**, so the clearance is a point-estimate clearance and nothing stronger. Section 5.3 shows the
gain is not retrieval at all, which matters more than the interval.

**Cross-modal loss: 10.60 pp** (`q-gold-text` +13.00 minus the winner's +2.40).

### 5.2 The full table at k = 5, NEW500 / OLD500 / pooled

| query set | pop | intent recall@5 | vote acc@5 | saves | harms | net pp | filler recall@5 | echo |
|---|---|---|---|---|---|---|---|---|
| `q-draft` | NEW500 | 74.60 | 63.80 | 42 | 89 | −9.40 | 31.47 | 71.34 |
| | OLD500 | 69.40 | 59.40 | 46 | 97 | −10.20 | 25.76 | 67.13 |
| | pooled | 72.00 | 61.60 | 88 | 186 | −9.80 | 28.73 | 69.24 |
| `q-gold-text` | NEW500 | **93.80** | **86.20** | 88 | 23 | **+13.00** | **64.02** | 72.55 |
| | OLD500 | 92.20 | 82.80 | 94 | 28 | +13.20 | 59.11 | 68.54 |
| | pooled | 93.00 | 84.50 | 182 | 51 | +13.10 | 61.67 | 70.54 |
| `q-speech-glap` | NEW500 | 63.00 | 40.60 | 26 | 189 | **−32.60** | 35.28 | 36.07 |
| | OLD500 | 64.40 | 42.40 | 38 | 174 | −27.20 | 34.32 | 35.87 |
| | pooled | 63.70 | 41.50 | 64 | 363 | −29.90 | 34.82 | 35.97 |
| `q-speech-glap+state` | NEW500 | 77.60 | 75.60 | 21 | 9 | **+2.40** | 40.90 | **96.19** |
| | OLD500 | 73.60 | 72.60 | 23 | 8 | +3.00 | 39.11 | 96.79 |
| | pooled | 75.60 | 74.10 | 44 | 17 | +2.70 | 40.04 | 96.49 |

k = 1 and k = 10 are in `per-query-set-table.json` and move nothing: the winner's net is +2.40 /
+2.40 / +2.20 at k = 1 / 5 / 10 on NEW500, and `q-speech-glap`'s is −34.80 / −32.60 / −31.80.

Paired CI90 on NEW500 (`delta = right − left`, 10,000 replicates, seed 20260903, stratified by gold
scenario): `q-gold-text` over `q-draft` **+22.40** [+19.20, +25.60]; `q-speech-glap+state` over
`q-draft` **+11.80** [+8.80, +14.60]; `q-speech-glap+state` over `q-speech-glap` **+35.00**
[+31.20, +39.00]; `q-speech-glap` over `q-draft` **−23.20** [−27.40, −19.00].

### 5.2b The per-stratum table (net corrective pp, NEW500, k = 5)

Every verdict on this program carries its per-stratum table; the complete one, for every set, k
and population, is `per-scenario-table.json`.

| scenario | n | glap+state net | glap net | gold-text net | draft net | glap+state recall@5 | glap recall@5 |
|---|---|---|---|---|---|---|---|
| `alarm` | 30 | +3.33 | -46.67 | -3.33 | +3.33 | 90.00 | 63.33 |
| `audio` | 2 | +0.00 | -50.00 | +0.00 | +0.00 | 100.00 | 100.00 |
| `calendar` | 33 | +3.03 | -24.24 | +21.21 | +3.03 | 72.73 | 60.61 |
| `cooking` | 9 | +11.11 | -22.22 | +11.11 | +0.00 | 77.78 | 77.78 |
| `datetime` | 33 | +3.03 | -21.21 | +12.12 | -66.67 | 87.88 | 81.82 |
| `email` | 33 | +3.03 | -51.52 | +9.09 | +0.00 | 87.88 | 60.61 |
| `general` | 33 | +0.00 | -21.21 | +9.09 | -12.12 | 36.36 | 36.36 |
| `iot` | 33 | +0.00 | -36.36 | +3.03 | +3.03 | 90.91 | 75.76 |
| `lists` | 32 | +0.00 | -40.62 | +3.12 | +0.00 | 84.38 | 62.50 |
| `music` | 23 | +0.00 | -43.48 | -17.39 | -78.26 | 82.61 | 47.83 |
| `news` | 32 | +3.12 | -28.12 | +9.38 | +3.12 | 84.38 | 81.25 |
| `play` | 32 | -9.38 | +0.00 | +50.00 | +28.12 | 43.75 | 75.00 |
| `qa` | 32 | +9.38 | -28.12 | +18.75 | -12.50 | 71.88 | 62.50 |
| `recommendation` | 32 | +12.50 | -34.38 | +34.38 | +0.00 | 78.12 | 34.38 |
| `social` | 33 | -3.03 | -39.39 | +12.12 | -21.21 | 75.76 | 60.61 |
| `takeaway` | 12 | -8.33 | -66.67 | +8.33 | -41.67 | 83.33 | 50.00 |
| `transport` | 33 | +12.12 | -18.18 | +24.24 | +0.00 | 81.82 | 72.73 |
| `weather` | 33 | +0.00 | -48.48 | +3.03 | +0.00 | 93.94 | 63.64 |

`q-speech-glap` is negative in **17 of 18 scenarios** (only `play` is level), from -18.18 on
`transport` to -66.67 on `takeaway`. The winner is small and mixed everywhere: its best stratum
is `recommendation` (+12.50) and its worst is `play` (-9.38), and no stratum carries the verdict.
`audio` (n = 2) is too small to read and is shown only for completeness.

### 5.3 The winner's gain is label legalisation, not neighbour evidence

The preregistered closed-form prediction of section 3 is confirmed exactly. The fusion's dominance
margin is 0.8 raw cosine, SLURP cosines live far inside that, and **the echo rate is 96.19 %** —
the neighbours' majority simply repeats the draft's own label. Recall@1 equals vote@1 (75.60), and
vote accuracy is identical at k = 1 and k = 5: the "retrieval" is not selecting between candidate
intents at all.

The remaining 3.8 % is where the whole measured gain lives, and it is not evidence:

* the sealed draft's own intent accuracy on these same rows is **74.20** (NEW500), **71.00**
  (OLD500), **72.60** (pooled) — the pooled figure reproduces the KU-S1c verdict's draft-phase
  intent of 72.60 exactly, which is this read's identity anchor;
* the sealed baseline is 73.20 / 69.60 / 71.40, so **the draft label alone is already +1.00 pp over
  the baseline on NEW500**;
* `q-speech-glap+state` reaches 75.60 / 72.60 / 74.10, i.e. **+1.40 pp above the draft label it
  echoes**;
* that +1.40 pp comes entirely from the **20 NEW500 rows (37 of 1,000) whose draft intent is not
  one of TRAIN's 60 intents** — 19 that parsed but named a label outside the ontology, plus 1 that
  did not parse at all. For those rows the prior dimension recalls nothing, the ranking falls back
  to pure GLAP speech, and the vote is at least a *legal* SLURP label where the draft's own answer
  was outside the ontology and therefore certainly wrong. The arithmetic closes exactly: echo is
  scored on the 499 parsed rows, 96.19 % of them echo, and the 19 non-echoes are precisely those
  out-of-ontology rows.

So the +2.40 pp decomposes as **+1.00 pp draft label + ~+1.40 pp closed-list legalisation of
out-of-ontology draft labels + ~0 pp retrieved evidence**. Legalisation is a decoding-constraint
repair available far more cheaply than a retrieval plane, and the fact that a closed-list arm still
emits 37 out-of-ontology labels per 1,000 is a finding in its own right — one for the prompt/decode
side, not the knowledge side.

### 5.4 Speech alone is worse than no retrieval at all

`q-speech-glap` votes correctly on 40.60 % of NEW500 rows against a 73.20 baseline and harms 189 of
366 correct rows. It is negative in **17 of 18 scenarios** (only `play` is level), from −18.18
(`transport`) to −66.67 (`takeaway`). It is not that the signal is absent — intent recall@10 is
76.20, so the gold intent usually IS somewhere in the ten neighbours — it is that the ranking is far
too weak for a majority vote to find it. Note also that GLAP's audio and text towers give the
*fillers* a fair showing (filler recall@5 35.28, higher than `q-draft`'s 31.47, paired delta +2.64
CI90 [−0.42, +5.64], includes zero), so the failure is specific to intent discrimination.

### 5.5 The text ceiling says the loss is cross-modal

`q-gold-text` is strong on every axis: recall@5 93.80, vote 86.20, net **+13.00 pp**, filler recall
64.02 (paired +22.59 over `q-draft`). **The gold-text branch is therefore NOT closed** — neighbour
voting over TRAIN utterance texts genuinely carries 13 pp of corrective power on SLURP intent when
the query is the transcript. What is closed, on this evidence, is reaching that ceiling with GLAP
as the speech encoder: 10.60 pp of the 13.00 is lost crossing the modality gap, and the 2.40 that
survives is the draft's own label rather than a neighbour.

### 5.6 What this licenses

* **Do NOT fly KU-S1-prime on `q-speech-glap` or `q-speech-glap+state`.** The gate's point estimate
  is cleared by a set whose vote is 96 % its own input; there is no retrieval mechanism to admit,
  and its CI90 lower bound sits below the gate besides.
* **The GPU sets of section 6 become the real test**, and they are now well posed: a speech encoder
  is a candidate only if it closes a meaningful share of the 10.60 pp cross-modal gap *with the
  prior dimension switched off*, i.e. as `q-speech-lco` / `q-speech-nemotron` rather than their
  `+state` variants. Judge the `+state` variants only against their own speech-alone set, and
  discount any gain whose echo rate is near 100.
* **Report the echo rate for every future retrieval cell on this carrier.** `q-draft` — the signal
  the lock actually uses — echoes 71.34 % and its vote is 9.40 pp *worse* than not retrieving at
  all. That is the strongest single reason MF-7 was worth running before another consumption cell.
* Filler recall does not gate and did not decide anything here, but for the record the winner's
  40.90 beats `q-draft`'s 31.47 by +6.54 CI90 [+3.75, +9.35] — the slot side of a retrieval plane
  remains the more promising half, consistent with KC-S1b.

## 6. The GPU steps — prepared, not run

Mandatory follow-on, written so a fresh agent can run it verbatim after the current KC-A1 flight
releases the GPU. **Section 6.2's loader question was already settled empirically** by a
four-contact CPU probe under `SAEA-SLURP-MF7-EMBEDDING-CPU-V1`; everything below rests on
measurements, not on reading llama.cpp source. Register the row **before** the first contact:

> **`SAEA-SLURP-MF7-EMBEDDING-GPU-V1`** — tool-level speech/text encoders on the GPU; **0
> frozen-core contacts**. Two encoders over the same 1,000 DEV-1000 recordings and 11,514 TRAIN
> utterance texts MF-7 already used on CPU: (a) **LCO-Embedding-Omni-3B** (`models/lco-embedding-omni-3b-gguf`,
> `LCO-Embedding-Omni-3B-Q8_0.gguf` + `mmproj-LCO-Embedding-Omni-3b-F16.gguf`) through the pinned
> featcache `llama-server --embedding --pooling last`, audio delivered as base64 through the
> multimodal prompt shape; (b) **Omni-Embed-Nemotron-3B** (`models/omni-embed-nemotron-3b`) in bf16
> on CUDA, both modalities. Both write the SAME `saea-mf7-vectors-v1` JSONL schema as the CPU pass
> (`{"id": ..., "vector": [...]}`), so `scripts/run_slurp_retrieval_key_audit.py` re-runs unchanged
> with `--query-set`. Every forward pass is counted; no completion or chat endpoint is contacted;
> the SLURP `test` split is never named; no devel sentence text is written anywhere. Vectors land
> under `SPEECHRL_DATA_DIR/vectors/slurp-mf7/` and never enter Git.

### 6.1 Preconditions

* `nvidia-smi` shows no other resident server, or only one whose owner has released the card.
* **Check the power state first** (`nvidia-smi --query-gpu=enforced.power.limit --format=csv`): a
  low cap means Legion SmartFanMode is throttling and the timings below are meaningless. During this
  audit the card sat idle at **0 MiB used with an enforced limit of 100.00 W** — verify that reading
  before trusting any throughput number, and raise it if the machine is in a quiet profile.
* `export PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=<repo>/src`, `SPEECHRL_DATA_DIR=…`, and **do not**
  `pip install` anything into the shared venv.
* Both `dev-rows.jsonl` and `train-facets.jsonl` already exist under
  `SPEECHRL_DATA_DIR/vectors/slurp-mf7/` — the GPU pass reuses them and must not regenerate them.

### 6.2 (a) LCO-Embedding-Omni-3B through llama-server

**The loader question is ANSWERED — LCO works, and it was proven on CPU under this audit's own
ledger row, not argued from source.** The probe ran the exact server below with `-ngl 0`, zero GPU,
and made four embedding contacts. Results, all reproducible:

* the GGUF **loads** on the pinned featcache build `04ccc72a` (clean tree, binary sha256
  `d0b42ace…404f2`) despite having been converted by the `ht-llama.cpp` fork. The server logs
  `[mtmd] estimated worst-case memory usage of mmproj is 3259.86 MiB` and
  `init_audio: audio input is in experimental stage and may have reduced quality`;
* **`GET /props` reports `"modalities": {"vision": true, "video": true, "audio": true}`** — the
  mmproj carries a real audio tower;
* **text embedding works**: `{"content": ["set an alarm for nine am"]}` → a **2048-dim** vector in
  0.26 s;
* **audio embedding works**: a 3.46 s SLURP devel clip → a 2048-dim vector, **L2 norm 1.0000**, in
  32.6 s on CPU (8 threads). A second clip reproduced it at 32.9 s;
* **input-level fusion works**: audio plus a draft-intent string in ONE prompt returned a 2048-dim
  vector in 31.1 s.

**The one trap, and it costs an hour if you miss it.** The server generates a **randomised media
marker** per process. Sending the documentation's literal `<__media__>` returns
`HTTP 500 {"error":{"code":500,"message":"Failed to tokenize prompt"}}`. You must read
`GET /props` → `media_marker` (observed once as
`<__media_FKVmu4P4bKJuEohVdSRSPvnBePAE6Btc__>`) and use **that exact string** as the
`prompt_string`. This repository already has the machinery:
`rails.embedding_client.resolve_expected_media_marker` plus `EmbeddingClient.verify_media_marker`,
which re-verifies the env-pinned marker against the live `/props` and fails closed. Use the real
client with `require_marker_verification=True` and `expected_dim=2048` rather than hand-rolling
`urllib`.

Two more settings the probe surfaced:

* the server warns `embeddings enabled with n_batch (2048) > n_ubatch (512)` and then **forces
  `n_batch = n_ubatch`**. Pass them equal (`-b 2048 -ub 2048`) so the geometry you record is the
  geometry you got;
* `--pooling last` is honoured over the model default (`model default pooling_type is [-1], but [3]
  was specified`), which is what puts LCO queries and LCO keys in one space.

```bash
# The real pass, on the GPU. Same argv as the probe except -ngl and -fa.
CUDA_VISIBLE_DEVICES=0 /home/chao/llama.cpp-featcache/build/bin/llama-server \
  --host 127.0.0.1 --port 8093 \
  -m $SPEECHRL_DATA_DIR/models/lco-embedding-omni-3b-gguf/LCO-Embedding-Omni-3B-Q8_0.gguf \
  --mmproj $SPEECHRL_DATA_DIR/models/lco-embedding-omni-3b-gguf/mmproj-LCO-Embedding-Omni-3b-F16.gguf \
  --embedding --pooling last -ngl 999 -c 8192 -b 2048 -ub 2048 -np 1 -fa on
```

**Memory envelope, from the server's own accounting rather than an estimate.** At `-ngl 0` it
projected **4,039 MiB** of host memory for the LLM and **3,259.86 MiB** worst case for the mmproj.
Offloaded, budget **about 7.5 GiB of the 24,463 MiB card**, plus CUDA context — call it 9 GiB with
headroom. Do not raise `-c` above 8192: SLURP clips average 2.9 s and a larger context only
enlarges the KV allocation.

**Requests.** Text keys go through the plain shape the CPU pass already used
(`{"content": [<text>, …]}`, batch 16). Audio queries go one per request through the multimodal
shape. Read the flac with `soundfile` and re-encode to 16 kHz mono PCM-16 WAV **with `soundfile`,
never ffmpeg** — ffmpeg is deliberately absent from this machine and installing it would change
audio bytes and cold the 26 GB feature cache:

```python
marker = json.loads(urlopen(f"{base}/props").read())["media_marker"]   # NOT "<__media__>"
wave, sr = soundfile.read(flac_path, dtype="float32")
buf = io.BytesIO(); soundfile.write(buf, wave, sr, format="WAV", subtype="PCM_16")
body = {"content": {"prompt_string": marker,
                    "multimodal_data": [base64.b64encode(buf.getvalue()).decode()]}}
```

Write `lco-q-speech-query-vectors.jsonl` (1,000 rows, id = DEV sample id) and
`lco-key-vectors.jsonl` (11,514 rows, id = facet id), plus an `lco.receipt.json` in the same
`saea-mf7-vectors-receipt-v1` shape the CPU pass emitted: embedder block (gguf + mmproj sha256,
build commit `04ccc72a2207347ca76161b93fd9d846dd0a8675`, binary sha256, argv, `/props`), per-set
`{file, count, dims, sha256, bytes, l2_norms, wall_seconds, throughput}`, and an `accounting` block
with `frozen_core_contacts: 0`, `gpu_hours`, `embedding_tool_contacts`, `speech_audio_seconds`.

**Input-level `+state` for LCO** (owner rule clause 2b): a second query pass in which the audio and
the sealed draft text are ONE multimodal input — `{"prompt_string": marker + "\n" + draft_text,
"multimodal_data": [b64]}` — written as `lco-fused-q-speech-query-vectors.jsonl`. **Proven to work
in the probe** (2048 dims, 31.1 s CPU). Register it as its own query set; it is distinct from the
rank-level `+state` the audit script computes, and it is the more interesting of the two, because
section 5.3 shows the rank-level variant degenerates into label echo.

**Expected cost.** 12,514 forward passes; the 1,000 audio queries dominate, since each ran 32.6 s
on 8 CPU threads while a text embedding took 0.26 s. Offloaded, expect a 30–60x speed-up on the
audio side, i.e. **roughly 10–20 minutes of audio plus a few minutes of text — budget 1 GPU-h and
stop if it exceeds that.** These are extrapolations from the CPU probe, not measurements; record
the real throughput in the receipt.

### 6.3 (b) Omni-Embed-Nemotron-3B on CUDA

**A blocker found offline, and its documented way round.** The model ships a
`sentence_bert_config.json` naming `sentence_transformers.base.modules.transformer.Transformer`
(sentence-transformers ≥ 5.4.0.dev0). **`import sentence_transformers` currently RAISES in the
shared venv**: it pulls `torchcodec`, which cannot load `libavutil.so.{58,59,60}` because **ffmpeg
is deliberately absent from this machine and must never be installed** (installing it would change
audio bytes and cold the 26 GB feature cache). The exact error is
`RuntimeError: Could not load libtorchcodec … OSError: libavutil.so.60: cannot open shared object
file`.

Therefore **do not use the sentence-transformers wrapper**. Load the model through plain
`transformers` and reproduce its three modules by hand — they are fully specified by the shipped
config and there is nothing to guess:

* module 0: `NVOmniEmbedModel` (`modeling_nv_omni_embed.py`, `trust_remote_code=True`) — a
  `Qwen2_5OmniThinkerForConditionalGeneration` whose text tower is made **bidirectional**
  (`is_causal = False` on every layer); take the last hidden state;
* module 1 (`1_Pooling/config.json`): **mean** pooling over the attention mask, `include_prompt:
  true`, 2048 dims;
* module 2: L2 normalise.

Inputs go through `Qwen2_5OmniProcessor` (`preprocessor_config.json`: `WhisperFeatureExtractor`,
128 mel bins, 16 kHz). The prompts from `config_sentence_transformers.json` are **`"query: "` for
the DEV speech queries and `"passage: "` for the TRAIN text keys** — use them, they are part of the
model's contract. Run bf16 on CUDA with `attn_implementation="sdpa"` (do not reach for flash-attn).
If `import sentence_transformers` is ever needed for something else, the only sanctioned
workaround is to make `torchcodec` unimportable for that process — never to install ffmpeg.

**Memory envelope.** 9.41 GB of safetensors in bf16 ≈ **9.5 GiB of weights**, plus activations for a
batch of 8 audio clips ≈ 2–3 GiB → **about 13 GiB of 24,463 MiB**. Comfortable alone; it will NOT
co-reside with a q4km 30B decoder, so this pass needs the card to itself.

Write `nemotron-q-speech-query-vectors.jsonl`, `nemotron-key-vectors.jsonl` and
`nemotron.receipt.json` in the same schema, plus the input-level fusion set
`nemotron-fused-q-speech-query-vectors.jsonl` (audio and the sealed draft text in ONE message, the
`message` modality of `sentence_bert_config.json`). **Expected cost: 15–30 minutes, under 0.5
GPU-h.**

### 6.4 Re-running the audit

No code change is needed. Drop the JSONL pairs into `SPEECHRL_DATA_DIR/vectors/slurp-mf7/` and:

```bash
python scripts/run_slurp_retrieval_key_audit.py --write \
  --query-set q-draft --query-set q-gold-text \
  --query-set q-speech-glap --query-set q-speech-glap+state \
  --query-set q-speech-lco --query-set q-speech-lco+state \
  --query-set q-speech-lco-fused \
  --query-set q-speech-nemotron --query-set q-speech-nemotron+state \
  --query-set q-speech-nemotron-fused
```

The catalogue in `scripts/run_slurp_retrieval_key_audit.py` already carries all ten names, their
file names, their encoders and their `contains_speech` / `fuses_state` flags. The decision table
re-applies itself over whatever sets are present. The `-fused` sets carry `fuses_state = False`:
the fusion happened inside the encoder, so no ranker term is applied on top of it.

Budget about 4.5 minutes of CPU per four query sets — the run is dominated by the stratified
bootstrap, not by the cosine matrices.

### 6.5 The Qwen3-Omni option — priced, not run

The frozen core's own encoder is the one speech representation guaranteed to be in the same space
the answering model reasons in. Using it as a retrieval key would mean pooling the featcache
encoder features for **TRAIN packets**, and that is the whole cost:

* the 11,514 TRAIN utterances have **50,628 recordings**; a key per utterance needs one packet per
  chosen recording. Even at one recording per utterance that is 11,514 new speech packets against
  the 1,000 DEV packets that already exist;
* SLURP TRAIN audio for one recording per utterance is roughly **9.5 hours** (11,514 × ~2.97 s), and
  the September packet pipeline encodes at roughly 60× realtime on the mmproj path, so **about
  10 minutes of pure encoder time** — but the packets themselves are the cost: at the observed
  featcache packet size this adds **tens of GB** to the 26 GB cache, and the cache is hash-pinned;
* pooling is not defined for this path. The frozen core exposes no pooled sentence embedding; a
  mean over encoder frames is an **invented representation**, exactly the kind of self-invented
  metric the 2026-08-25 owner ruling told this study to stop producing while the agent layer is
  unconverged;
* and it needs the GPU for the whole build, in competition with real cells.

**Recommendation: do not run it.** If a later owner decision wants it, it should be its own
prerequisite with its own preregistration of the pooling definition, not a clause of MF-7.

## 7. Limits carried

* DEV-1000 is prior-exposed as a whole; NEW500 is the only unexposed half and is the decision
  population. Nothing here transfers to the held-out `test` split, which was never named or loaded.
* The audit measures what neighbours *contain*, not what a frozen core would *do* with them. A set
  that clears the gate has shown an upper bound on a voting consumer, not an admitted cell.
* Every number is offline arithmetic over sealed bytes plus tool-level encoders. No frozen-core
  contact was made, so nothing here revises any published arm's score.
* **The negative result is GLAP-specific, not speech-specific.** One speech encoder was measured.
  The claim "a speech query is not a viable retrieval key on SLURP" is licensed for GLAP only; the
  10.60 pp cross-modal gap is what the section 6 encoders exist to attack, and until they run the
  general statement is unproven in both directions.
* The corrective-power metric assumes a MAJORITY-VOTE consumer. A consumer that weighted
  neighbours by similarity, abstained below a threshold, or supplied the neighbours as evidence to
  the frozen core rather than voting could do better than these numbers on the same neighbours —
  most visibly for `q-speech-glap`, whose recall@10 of 76.20 is far above its vote accuracy of
  41.40. What the audit rules out is the vote, not every possible use.
* One knob was inherited rather than chosen: the `+state` fusion uses the registered ranker's
  weights unchanged, by the owner's "no new knob" instruction. A different `w_prior` would trade
  echo against speech, and the audit did not explore that surface.
