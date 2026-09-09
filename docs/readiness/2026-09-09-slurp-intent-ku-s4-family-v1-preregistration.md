# SLURP intent narrowing and speaker exemplars — the KU-S4 family, preregistration v1 (2026-09-09)

**Owner Decision 10 of 2026-09-08**: KU-S4N candidate narrowing only, then KU-S4a same-speaker
audio exemplars with twins KU-S4b (other speaker) and KU-S4c (TRAIN gold text).

**Status: REGISTERED, NOT FLOWN. Zero model contacts were spent preparing it** — zero frozen-core,
tokenizer, embedder, retriever, network, GPU and paid-API contacts; no audio sample decoded. Every
number below is model-free and re-derivable from committed bytes, governed corpus bytes, sealed
outputs and sealed vectors (`SAEA-SLURP-MF-KU-S4-PREP-V1`, receipts
`docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-kus4-prep/` and
`…/2026-09-09-slurp-kus4-wire-check/`).

Predecessors this note is built on and does not restate:
`docs/readiness/2026-09-08-mf8-speech-to-knowledge-audit-v1.md` (the price: candidate sources,
speaker structure, multi-packet transport, exemplar availability),
`docs/readiness/2026-09-09-slurp-own-null-replicate-v1-verdict.md` (the margins),
`docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md` (the four agents, the
core-pressure covariates, the module admission gate),
`docs/readiness/2026-09-08-slurp-slot-knowledge-views-kv-v1-preregistration.md` (the template),
`docs/readiness/2026-09-06-slurp-legal-label-projection-v2-verdict.md` (the comparator).

---

## 0. The answer this family is buying

The sealed closed-list comparator hands the frozen core **60 labels and 2,146 tokens of inventory**
and asks it to pick one; it gets 73.10 % of them right. This family asks whether the SYSTEM can take
most of that decision away and do better.

| what the system decides | how | measured, before any flight |
|---|---|---:|
| the candidate set | the comparator's own predicted scenario's legal intents + the row's own speech-vector neighbours | the gold intent is inside it on **95.80 %** of all rows and **86.62 %** of the rows the core gets wrong |
| how much is removed from the core | k of 60 | **9.89 %** of the label space offered at the realized mean, 13.33 % at the cap |
| the legality flag | `slurp-legal-label-flag-v1`, deterministic, 0 core calls | **42 of 1,000** rows flagged, **25** of them still wrong after the projection |
| the answer | the frozen core, **one call per row**, unchanged | — |

**The reachable ceiling is 96.40 intent**, not 100: a perfect matcher over this candidate set
recovers at most 233 of the 269 current errors. Every rule below is measured against that.

---

## 1. The family

| cell | run id | what the core additionally sees | comparator(s) |
|---|---|---|---|
| **KU-S4N** | `SAEA-SLURP-KUS4N-CANDIDATES-DEV1000-V1` | k typed candidate-intent blocks, gold-free | sealed closed-list rows **and** the sealed KU-S4N-t rows |
| **KU-S4N-t** | `SAEA-SLURP-KUS4N-CANDIDATES-TWIN-DEV1000-V1` | the same count of candidate blocks, drawn at random from the intents KU-S4N did **not** choose | sealed closed-list rows (read as a control, never admitted) |
| **KU-S4a** | `SAEA-SLURP-KUS4A-SPEAKER-EXEMPLARS-DEV1000-V1` | KU-S4N's blocks **plus** one `key`-role audio packet per covered candidate, of **this row's own speaker** producing that intent | sealed KU-S4N rows |
| **KU-S4b** | `SAEA-SLURP-KUS4B-OTHER-SPEAKER-DEV1000-V1` | the same slots, filled by **other** speakers | read only as `KU-S4a − KU-S4b` |
| **KU-S4c** | `SAEA-SLURP-KUS4C-TEXT-EXEMPLARS-DEV1000-V1` | the same slots, as the exemplars' **TRAIN gold sentence text** instead of audio | read only as `KU-S4a − KU-S4c` |

**KU-S4a, KU-S4b and KU-S4c are BLOCKED** on the packet-promotion precondition of section 7. They
are registered here so the precondition has something to be a precondition *of*; **no contact may be
spent on them until that row closes.**

---

## 2. KU-S4N — the candidate view

### 2.1 The rule, and it sees no gold

For each DEV-1000 row, in this order (`rails.slurp_intent_candidates.compose_candidate_set`):

1. the **predicted scenario's legal intents**, TRAIN prior first, at most three — read off the
   comparator's own sealed response through `reproduction.slurp_scoring.project_slu_label_v2`, the
   paper-facing scorer's own label path;
2. the **speech-vector neighbours' distinct intents** in cosine rank order over the top 50
   neighbours, skipping repeats, until the set holds k = 8.

The query vector is the sealed `q-speech-nemotron` embedding of **the row's own recording** and
nothing else — the owner's 2026-09-06 rule holds as a fact about the file, not as a promise. Neither
half can see a gold label: half (1) is the arm's own mistake and half (2) is a cosine.

### 2.2 k = 8 is a CAP, not a count — and the cap is the right knob

This preparation found something MF-8's own tables do not show. At the registered neighbour depth the
rule **runs out of distinct neighbour intents** before it fills eight slots on most rows:

| candidates offered | 1 | 2 | 3 | 4 | 5 | 6 | 7 | **8** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rows | 12 | 57 | 103 | 136 | 110 | 83 | 82 | **417** |

Mean **5.94** candidates per row; the realized narrowing ratio is **9.89 %**, not 13.33 %. The
scenario lead itself contributes three intents on only 682 rows (two on 192, one on 123, none on 3 —
measured, exactly the three rows whose sealed response does not parse at all, so the projection has no
scenario to offer a legal list for).

**Deepening the neighbour list buys nothing where it matters**, and that is measured rather than
assumed:

| neighbour depth | mean candidates | rows at the full 8 | gold in set, all rows | **gold in set, error rows** | realized narrowing |
|---|---:|---:|---:|---:|---:|
| **50 (registered)** | **5.94** | 417 | **95.80** | **86.62** | **9.89 %** |
| 100 | 6.93 | 647 | 95.90 | **86.62** | 11.55 % |
| 200 | 7.76 | 872 | 95.90 | **86.62** | 12.94 % |
| 400 | 8.00 | 998 | 95.90 | **86.62** | 13.33 % |

**Eight times the neighbour list buys +0.10 pp on all rows and exactly zero on the rows the core gets
wrong**, at a third more of the label space handed back to the core. The registered depth is
therefore not a default that survived inspection; it is the better arm on the only population the
mechanism is aimed at. **The per-row offer and its narrowing ratio are reported as covariates**, and
the twin matches each row's own count by construction, so the FORM contrast is exact regardless.

### 2.3 Reach, on every population

| population | n | gold in KU-S4N's set | gold in the twin's set |
|---|---:|---:|---:|
| all rows | 1,000 | **95.80** | 0.60 |
| the comparator's error rows | 269 | **86.62** | 1.86 |
| NEW500 (the decision population) | 500 | **95.40** | 0.60 |
| error rows inside NEW500 | 124 | **83.87** | — |

The arm's **own prediction is inside its own candidate set on 983 of 1,000 rows** (98.3 %), so the
mechanism is a narrowing and not a substitution: on almost every row the core may still answer what
it answered before.

### 2.4 What a block says, and where it does not go

One value per legal intent, one fixed template, delivered as **traced supply** —
`evidence_id` / `source_uri` / `knowledge_role="value"` — never in the instruction:

> `Candidate intent for the spoken command in this request: alarm_set (scenario "alarm", action "set").`

The block is self-describing because the instruction may not be told about the mechanism: the system
message is held **byte-identical** to the sealed comparator's, sha256
`4073f79ef25c4796b0a46cb2ac7f5d4982c83084982b87ddd8a70504090d37db`, 7,583 characters.

The facet (KEY) side is deliberately not a bare label name
(`intent candidate key: alarm_set`), and that is a finding rather than a style choice: the
comparator's own closed label inventory already names all sixty intents, and
`rails.runner._protected_knowledge_material` protects every facet representation of 8 characters or
more — a bare-name facet would make the containment fold refuse the very instruction this family
holds fixed.

**Containment, measured over the snapshot's 120 protected payloads:**

| fold | what it asks | result |
|---|---|---:|
| **C1** | does a supplied payload occur inside the arm's own CONTROL turn? — the fold `rails.runner._assert_agent_control_excludes_knowledge_payloads` runs at contact time | **0** |
| **C2** | does a supplied payload occur inside the SYSTEM message? | **0** |
| **C3** | does the view's own payload occur inside the instruction that carries it? | **0** — the number KU-S3 also keeps, and the one the KV family could only report as 100 % |

### 2.5 The twin, and what makes it a control

`rails.slurp_intent_candidates.compose_twin_set` draws exactly as many intents as KU-S4N offered
that row, uniformly at random from the 60 legal intents **excluding every intent KU-S4N chose**,
with `random.Random(f"20260903:{sample_id}")` — one seed whose only entry point is the sample id.

Excluding the arm's own choices is what makes this a control rather than a weaker arm: a draw that
could contain the candidate KU-S4N found would measure "does narrowing help" twice instead of "does
the RIGHT narrowing help". Measured, the twin reaches the gold on **0.60 %** of rows.

**Volume, the reported covariate** (owner ruling 2026-09-06: the twin is the lock, not a token
count). One fixed template per candidate means arm and twin differ only in the label names they
carry:

| | min | median | mean | max |
|---|---:|---:|---:|---:|
| arm block characters | 102 | 715 | **652.3** | 943 |
| twin block characters | 104 | 701 | **655.4** | 949 |
| absolute delta | 0 | 16 | **19.2** | 86 |
| arm / twin token proxy | 19 | 110 | **108.45 / 108.45** | 146 |

### 2.6 The two things that move against the sealed comparator, stated rather than claimed away

A supplied phase can only be expressed as a phase program, and a phase program adds **one ORG/CONTROL
history turn** carrying `configs/probes/slurp_phase_direct.txt` (262 characters, sha256
`d02f194c…f9d50`, 56 proxy tokens). The sealed comparator flew `policy: "fixed"` with no history at
all. So against the sealed rows **two things move**: the supplied blocks and that control turn.

This is why the family reads **two** contrasts and admits on both:

* **against the sealed comparator** — the deployment contrast, carrying the control turn as a
  declared covariate;
* **against the sealed twin** — the mechanism contrast, in which the control turn, the program, the
  channel, the block template and the block count are all identical and only the candidate content
  differs.

`configs/baseline/slurp-phase-direct-only-v1.json` is the form-null this family did NOT register: it
is the same program with no supply, and if the two contrasts disagree in sign it is the cell that
would decide which of the two moved the number. It is named here so a successor can register it
deliberately rather than discover the need for it.

### 2.7 The judge, and why it is free

`phase_review.direct` declares `slurp-legal-label-flag-v1` with `on_flag: "record"`, which
**changes not one byte of what the flight sends** (`rails.phase_review` module docstring). Measured
on the comparator's own sealed rows, the judge flags **42 of 1,000** — 21 illegal scenario, 18
illegal action for the named scenario, 3 unparsed — of which the projection already repairs 17 and
**25 stay wrong**. It is a core-pressure covariate, never a decision criterion, and this family
spends no contact on it.

---

## 3. KU-S4a / KU-S4b / KU-S4c — the exemplar arms

### 3.1 The exemplar plan, per candidate slot

| arm | what fills a slot | selection rule |
|---|---|---|
| **KU-S4a** | one TRAIN recording of **this row's own speaker** producing that candidate intent, as a `key`-role packet | first by `(utterance_id, sample_id)` — deterministic, seedless |
| **KU-S4b** | one recording of the same candidate intent by a **different** speaker, in exactly the slots KU-S4a filled | `random.Random(f"20260903:{sample_id}:{intent}").choice` |
| **KU-S4c** | the **same** recordings KU-S4a names, as their TRAIN gold **sentence text** | identical slots, identical utterances |

**The fallback for an uncovered slot is NO exemplar, and it is counted** (owner Decision 10). MF-8
named three options and said each contaminates a different factor; this is the one that contaminates
none — it changes the DOSE on some rows rather than the FACTOR on any row, and the dose is a reported
covariate and a pre-declared stratum.

Binding KU-S4b to exactly the slots KU-S4a filled is what makes the speaker contrast clean: same
slots, same count, different voice.

### 3.2 Coverage, measured

| quantity | value |
|---|---:|
| candidate slots offered over the roster | **5,937** |
| slots the row's own speaker can fill | **5,442** |
| slot coverage, pooled / mean-per-row | **91.66 % / 92.14 %** |
| **uncovered slots (the fallback)** | **495 (8.34 %)** |
| **rows every slot of which its own speaker covers** | **658 (65.80 %)** |
| … of which NEW500 | **341** |
| rows with no exemplar at all | **3** |
| slots filled per row, min / median / mean / max | 0 / 6 / **5.44** / 8 |
| rows whose GOLD intent's slot is filled | **902** |
| distinct same-speaker exemplar recordings | **2,742** |
| distinct other-speaker exemplar recordings | **5,082** |

**The primary population for KU-S4a is the whole roster, decided on NEW500 (n = 500).** The
fully-covered stratum (658 rows, 341 of them NEW500) is a **pre-declared secondary read** and, at
341, does **not** clear the program's n ≥ 400 paired-claim floor — so no effectiveness claim may be
made on it, in either direction. That is MF-8 section 5.2's trade, taken with eyes open: the k that
maximises reach and the k whose clean stratum clears power are not the same k, and this family
chooses reach and reports the clean stratum as a covariate.

### 3.3 The modality confound, and it is smaller than MF-8 feared

MF-8 warned that the text twin would cost about a quarter of the audio arm per exemplar. Measured on
this plan:

| arm | metered speech, one pass | exemplar audio tokens / row (mean, max) | text characters / row (mean, max) |
|---|---:|---:|---:|
| KU-S4a | **18,103.40 s** | 233.1 / 572 | — |
| KU-S4b | **18,637.42 s** | 239.6 / 468 | — |
| KU-S4c | **2,884.79 s** | — | **174.2 / 393** (≈ 46 / 103 proxy tokens) |

**The audio arms cost ≈ 233 prompt tokens per row where the text arm costs ≈ 46** — a factor of five,
not four. The modality contrast is therefore **not token-matched and may never be claimed as such**;
supplied volume is a reported covariate on every KU-S4c number.

### 3.4 The multi-packet request, proved

The transport already carries N packets per request (MF-8 section 3.1 read the pinned server source);
what this preparation adds is the proof that a one-query-plus-k-keys request **composes through the
real code**, with zero sockets and zero contacts
(`docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-kus4-wire-check/`, half
`multipacket`, **PASS**):

| stage | real component | result |
|---|---|---:|
| policy | `core.policies.build_arm_payload("speech-feature-query", …)` | **9 descriptors** (1 query + 8 keys), exact D2 field set, one query |
| policy, negative | two queries / zero queries / an unknown role | **refused, all three**, by name |
| client parser | `rails.core_client._parse_speech_feature_messages` | **9** descriptors returned from 9 `input_speech_features` content parts beside a typed candidate block |
| transport ordering | `core.model.transport._ordered_speech_feature_content` | **9** media markers, in order |
| media identity | `core.model.speech_features.load_speech_feature_packets` | **9** packets loaded and hash-verified against the comparator's own feature root |
| body | `LlamaServerTransport` (needs an attested live session) | proved by the committed unit tests, run in the check |

The key packets in that proof are **real, already-promoted TRAIN encoder packets** used as SHAPE
stand-ins. The KU-S4a plan's own recordings are not promoted, which is section 7.

---

## 4. Order, and why

**KU-S4N → KU-S4N-t → KU-S4a → KU-S4b → KU-S4c.** One experiment in flight at a time.

1. **KU-S4N first, and it gates the family.** If narrowing alone does nothing, an exemplar attached
   to a candidate set that does nothing is a second factor on a dead first one. It is also the
   cheapest cell here: no exemplar audio, no packet promotion, the comparator's own metered speech.
2. **KU-S4N-t second**, before KU-S4N is read. The twin is not a follow-up: KU-S4N's own admission
   rule names its sealed rows, so the arm cannot be read until the twin has flown.
3. **KU-S4a third, and only after the packet-promotion precondition closes.** It is the owner's
   primary — dimension 2, same-speaker speech-domain knowledge.
4. **KU-S4b fourth**, the speaker twin. Attribution, never admission.
5. **KU-S4c fifth**, the modality twin. Attribution, never admission, and its volume confound is
   reported with every number.

**No cell in this family is a knob sweep.** k is not tuned, the neighbour depth is not re-drawn on
the strength of a number, the seed is not re-rolled, and a NULL result closes the line rather than
opening a search.

---

## 5. The decision rules, frozen before any read

`analysis.paired.paired_contrast`, delta = arm minus comparator on per-sample official scores,
**speaker-clustered** bootstrap (124 clusters), N = 10,000, seed 20260903, **CI90**, exact sign test.
The scenario-stratified family is reported beside it; the two cannot be crossed on this carrier.
Both weightings reported: natural mixture and equal-stratum. **A per-stratum table with every
verdict, without exception.**

Scoring is the dataset's standard scorer: the real, unmodified official `evaluate.py` at pinned
commit `8eb16545762be97ace75334109d73824217311f1`, `--average micro`, run **once over the complete
manifest** through `core.scoring_batch`, never sharded, with the official-vs-port identity check.
`slurp-slu-f1-normalized-v1` runs beside it as the secondary and must **agree in sign**.

### 5.1 The margins are SLURP's own, measured

From `SAEA-SLURP-DEV1000-NULL-REPLICATE-V1` (2026-09-09) — the same request flown twice:

| metric | margin (this null's own CI90 half-width) | the interval a claim must be DISJOINT from |
|---|---:|---|
| **intent (scenario+action)** | **0.9195** | **[−0.4049, +1.4341]** |
| scenario | 0.8255 | [−0.4188, +1.2322] |
| action | 0.9790 | [−0.5882, +1.3699] |
| **SLU-F1 (micro, paper-facing)** | **1.1804** | [−0.9088, +1.4521] |

**The disjointness bar, stated as a number before anything flies: an intent CI90 lower bound above
+1.4341.** At this carrier's measured half-width of 0.9195 that needs a point estimate of about
**+2.4 pp**, and a mechanism that moves intent by less than roughly **2 pp is not separable from
this carrier's own greedy replicate noise** — which moved intent +0.50 pp with nothing changed at
all.

### 5.2 KU-S4N

**ADMITTED** iff, on the unexposed **NEW500**:

* the paired **intent** CI90 lower bound is **above 0 against the sealed comparator rows** AND
  **above 0 against the sealed twin rows**; and
* the intent interval against the comparator is **disjoint from the null's own interval**
  (lower bound > **+1.4341**); and
* official **SLU-F1**, **scenario** and **action** are non-inferior at their own measured margins
  (CI90 lower bound above −1.1804 / −0.8255 / −0.9790); and
* the normalized secondary agrees in sign on both contrasts.

**NULL** if any of the two intent intervals includes 0: narrowing closes on this carrier and the
exemplar arms do not fly. **HARMFUL** if an upper bound is below 0.

**A twin that BEATS the comparator is a finding in its own right** and, if it does, KU-S4N is not
admitted on the strength of the comparator contrast: it would mean the family is measuring supply
volume rather than supply content.

**Per-scenario harm is REPORTED, not gated.** The own-null verdict showed a cell with no factor
losing intent on 5 of 18 scenarios and up to 5.13 pp, so the EVO-S1 clause ("at most 2 of 18 lose
anything, none by more than 3.0 pp") is not a discriminating gate at n = 30 to 61 per stratum and is
not used as one here.

### 5.3 KU-S4a, and its two twins

**KU-S4a is the only exemplar arm that can be ADMITTED**, and its comparator is the **sealed KU-S4N
rows** — the one factor between them is the exemplar packet.

* **ADMITTED** iff the paired intent CI90 lower bound on NEW500 is above 0 against sealed KU-S4N,
  the interval is disjoint from the null's, SLU-F1 / scenario / action are non-inferior at their own
  margins, and the normalized secondary agrees in sign.
* **KU-S4b and KU-S4c are ATTRIBUTION, never admission.** They are read on the same rows, never
  pooled with the primary, never selected after the fact, and neither can rescue KU-S4a.
  `KU-S4a − KU-S4b` is the **speaker** effect; `KU-S4a − KU-S4c` is the **modality** effect, and the
  latter carries the volume confound of section 3.3 on its face.
* The fully-covered stratum (658 rows / 341 NEW500) is reported for all three and **carries no
  claim**: 341 is below the n ≥ 400 floor.

### 5.4 Guards and covariates on every verdict

Core-pressure covariates (design note 2026-09-08 section 3), reported by every cell in this family:

* core calls per row — **1 by construction**, on every arm;
* core **prompt and completion tokens** per row, arm and twin;
* **the system's decision share**: the per-row narrowing ratio (candidates offered / 60), its mean
  and its distribution — the number that says how much of the answer the system produced;
* **judge interceptions**: flags raised, by code, and how many rows they cover — with `on_flag:
  "record"` no flag causes a revise, and the count is reported as such;
* **exemplar dose**: slots offered, slots filled, uncovered slots, and the fully-covered stratum;
* **supplied volume**: block characters and the exemplar audio seconds or text characters per row.

Guards, asserted rather than hoped: the system message sha256 equal to the sealed comparator's on
every row of every arm; exactly one CONTROL history turn per request; the containment fold raising
on none of them; and, for the twin, zero candidate overlap with the arm on every row.

---

## 6. Populations

| population | n | receipt | role |
|---|---:|---|---|
| DEV-1000-NEW500 | 500 | `docs/receipts/probe-samples/DEV-1000-NEW500.json` | **the decision population**; reported first |
| DEV-1000 pooled | 1,000 | `docs/receipts/probe-samples/DEV-1000.json` | reported; the replication stratum |
| DEV-500 (prior-exposed) | 500 | `docs/receipts/probe-samples/DEV-500.json` | reported separately, never pooled into a decision |
| fully-covered stratum | 658 (341 NEW500) | derived, construction-fixed | secondary read, **no claim** |

Split identity hash `8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84`. **No new draw
and no new exposure**: these are the rows the sealed lock arms, the closed-list comparator, KC-S1a,
KC-S1b, KU-S1c, the tail cell, the logprob probe and the own-null replicate have all already
contacted. Gold never enters the flight process — samples are built label-free from the runtime view
and the adapter's `gold()` refuses outright. **The held-out `test` split is never named, loaded or
scored.**

---

## 7. The packet-promotion precondition — KU-S4a and KU-S4b are BLOCKED

An exemplar reaches the core as a `key`-role **encoder packet**, and a packet has to exist. Measured
against every promotion receipt beside the comparator's own, in the comparator's own feature root
`/home/chao/feat-cache/slurp-q4km-packets-04ccc72a` at build commit `04ccc72a`:

| plan | recordings needed | already promoted | **to promote** |
|---|---:|---:|---:|
| KU-S4a (same speaker) | 2,742 | **162 (5.91 %)** | **2,580** |
| KU-S4b (other speaker) | 5,082 | **291 (5.73 %)** | **4,791** |
| **together** | 7,824 | 453 | **7,371** |

The root holds 2,673 TRAIN packets today, and they are the EVO-fold and knowledge-63 rosters — a
different selection entirely.

**Precondition row, preregistered here as a blocking clause:**

| | |
|---|---|
| row id | `SAEA-SLURP-KUS4-EXEMPLAR-PACKETS-V1` |
| profile | `model-free-check` (a preprocessing session; the encoder runs, the frozen core does not) |
| **frozen-core contacts** | **0** |
| recordings to promote | **7,371** |
| audio seconds to encode (upper bound) | **≈ 30,971** |
| GPU hours | **not pinned here** — it belongs to the packet-build receipt, which this preparation does not own and does not estimate |
| output | one promotion receipt per plan under the comparator's own feature root and build commit, its sha256 pinned into the KU-S4a and KU-S4b baseline fragments |
| gate | every packet's `decoder_gguf_sha256` and `mmproj_sha256` equal to the DEV-1000 receipt's, so the query and the keys are encoder-identical |

**Until that row closes with those receipts, KU-S4a and KU-S4b may not fly and their fragments may
not be written with a packet pin.** KU-S4c needs no packet at all — its exemplars are text — but it
is ordered after KU-S4a because it is that arm's twin and has nothing to attribute without it.

---

## 8. Budgets and geometry

Geometry is the sealed comparator's own and is held fixed by every arm:
`-c 65536 -np 8`, **8,192-token slots**,
`configs/model/q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64.json`.

| run id | calls (ceiling) | metered speech s (ceiling) | GPU-h (projected / ceiling) | tool | embedding | paid |
|---|---:|---:|---:|---:|---:|---:|
| `SAEA-SLURP-KUS4N-CANDIDATES-DEV1000-V1` | 1,000 + 8 (**1,050**) | 2,884.7937 (**3,000**) | ≈ 0.113 / **1.0** | 0 | 0 | 0 |
| `SAEA-SLURP-KUS4N-CANDIDATES-TWIN-DEV1000-V1` | 1,000 + 8 (1,050) | 2,884.7937 (3,000) | ≈ 0.113 / 1.0 | 0 | 0 | 0 |
| `SAEA-SLURP-KUS4A-SPEAKER-EXEMPLARS-DEV1000-V1` | 1,000 + 8 (1,050) | **18,103.40 (19,000)** | ≈ 0.124 / 1.0 | 0 | 0 | 0 |
| `SAEA-SLURP-KUS4B-OTHER-SPEAKER-DEV1000-V1` | 1,000 + 8 (1,050) | **18,637.42 (19,500)** | ≈ 0.124 / 1.0 | 0 | 0 | 0 |
| `SAEA-SLURP-KUS4C-TEXT-EXEMPLARS-DEV1000-V1` | 1,000 + 8 (1,050) | 2,884.7937 (3,000) | ≈ 0.115 / 1.0 | 0 | 0 | 0 |

**The whole family is ≈ 5,000 contacts and ≈ 0.59 GPU-h.** The expensive line is not GPU: it is
**metered speech**, and each audio arm books about **6.3×** the comparator's. That is the number a
budget registration has to carry, and it is the reason KU-S4N flies first — it books none of it.

Run-cumulative across every attempt of a run id, enforced by `core.model.adapter`. At most **one**
recovery re-registration per run id; a second failure stops the flight and the fix is proven on a
4-row dry run. Each run id needs its own exposure-ledger row, written before its first contact. Paid
API spend 0.

### 8.1 Prompt fit, projected — and measured before takeoff

On MF-10's whitespace proxy plus the source-read encoder rate (13 tokens per whole second,
`tools/mtmd/clip.cpp` `PROJECTOR_TYPE_QWEN3A`). **No tokenizer was called.**

| arm | prompt tokens, mean | worst case | slot headroom | fits 8,192 |
|---|---:|---:|---:|---|
| sealed comparator (realized) | 2,190.2 | — | 3.74× | — |
| **KU-S4N / KU-S4N-t** | **2,354.7** | 2,517 | **3.48×** | yes |
| **KU-S4a** | **2,587.7** | 3,089 | **3.17×** | yes |
| **KU-S4b** | **2,594.3** | 2,985 | **3.16×** | yes |
| **KU-S4c** | **2,400.6** | 2,563 | **3.41×** | yes |

Fixed instruction 2,146 tokens; control turn 56 proxy tokens; candidate blocks 108.5 mean / 146 max.
**Every arm fits with more than three times the headroom and no geometry change.** The fit is still
MEASURED, not assumed: before takeoff each arm runs the zero-generated-token `/apply-template` +
`/tokenize` pass over all 1,000 rows through the resident session, reports its worst envelope against
the 8,192-token slot and pins `prompt_fit_receipt` + `prompt_fit_receipt_sha256` into its fragment. A
negative margin STOPS the mission; `FlightRuntime`'s own pre-flight estimator is not evidence for a
cell like this.

### 8.2 The family runner

The five cells fly **back to back on one resident session** per the always-on serving note
(`docs/readiness/2026-09-07-always-on-serving-operating-note.md`): the flight ATTACHES through
`core.session.attach_session` at the session's own `-c 65536 -np 8` geometry and starts and stops
nothing. One entry point, `scripts/flights/run_slurp_closed_list_cell.py`, drives every cell of the
family — it gained exactly one config-driven binder, `_bind_ku_s4_material`, which loads the
sha256-pinned candidate bank behind the provider and the 60-pair legal inventory behind the judge
through `FlightRuntime.bind_phase_supply_providers` / `bind_phase_review_material`. **A fragment that
declares neither key is byte-unaffected.**

**One registration commit.** All five experiment fragments, their exposure rows and this note are
committed together before the first contact, so the family's identity is fixed by one tree state
rather than by five. A dirty tree at any point in a run's life refuses the finalize, so the checkout
stays clean for the whole family.

---

## 9. The episode, and the admission-table entries

| agent | what it does in a KU-S4 cell |
|---|---|
| **Planner** | fixed: one observe mode (the frozen DEV-1000 packet), one knowledge view (the candidate bank's selection), one budget of one core call per row, stop after Solve. The narrowing IS the Planner's choice |
| **Observer** | the sealed DEV-1000 speech packet, promotion receipt `2accbdc5…a8fe6`, unchanged on every arm. KU-S4a/b additionally deliver k `key`-role packets, which is a supply of already-materialized bytes rather than an observe mode |
| **Solver** | the frozen core, one contact per row, given the query recording and the candidate blocks |
| **Reviewer** | `slurp-legal-label-flag-v1` on the `direct` phase, `on_flag: "record"` — criticism only, and byte-free by construction |

`docs/receipts/harness-admission.json`, one row per module per carrier, written on closure:

| module | carrier | status | evidence |
|---|---|---|---|
| `knowledge view: gold-free intent candidate set (KU-S4N)` | SLURP | pending | `SAEA-SLURP-KUS4N-CANDIDATES-DEV1000-V1` vs the sealed comparator and vs `…-TWIN-…`, NEW500 |
| `judge: legal-label flag as a record-only reviewer` | SLURP | pending | the same cell's `phase_review` receipt; the module's switch is `judges.direct` and its null arm is the block absent |
| `knowledge view: same-speaker audio exemplars (KU-S4a)` | SLURP | pending | `SAEA-SLURP-KUS4A-SPEAKER-EXEMPLARS-DEV1000-V1` vs sealed KU-S4N |

The `legal-label projection judge | SLURP | ADMITTED` row already in that receipt is **not** restated
by this family: that entry is the scoring-side projection, and this one is the flight-side flag.

---

## 10. Wire check, and the state of the engineering

Receipt `docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-kus4-wire-check/`,
**PASS on all three halves**, 4 DEV-1000 rows per cell, **zero sockets, zero model contacts, zero
GPU**.

| assertion | KU-S4N | KU-S4N-t |
|---|---|---|
| model contacts | **0** | **0** |
| requests built | 4 of 4 | 4 of 4 |
| policy / contacts per sample | `phase-direct-only-supplied-v1` / **1** | same |
| `phase_supply` covers | **`direct`** only | **`direct`** only |
| typed knowledge blocks (sorted) | **5, 7, 8, 8** — each row's own candidate count | **5, 7, 8, 8**, identical |
| supplied evidence ids | all carry `value:intent-candidate:` | same, **sharing nothing with the arm** |
| control turn | one per request, sha256 `d02f194c…` | **the same sha256** |
| resolved system message | `4073f79e…0d37db` | `4073f79e…0d37db` |
| config hash / protocol hash | `5073bda3…` / `3044e0df…` | `38447fb8…` / `d12873c9…` — **distinct** |

Those two hashes are the WIRE-CHECK cells' own: that fragment declares its own four-row
`split_id` `DEV-1000-KUS4-WIRE-4`, so they are not the registered DEV-1000 cells' hashes and must
never be quoted as such. What the check proves is that the arm and its twin are two identities, not
which two.
| candidate bank | `a4458e77…` selection `candidates` | `a4458e77…` selection `twin_candidates` — **one file, both arms** |
| review material bound | `slurp-legal-label-flag-v1` | same |
| containment fold | raised on **none** of the 8 contacts | — |

The block counts are recorded SORTED and the per-row counts are keyed by sample id, because the
runtime reports them in DISPATCH order and two runs of the same cell may dispatch four rows in two
orders. **The receipt reproduces byte for byte across consecutive runs**, checked.

**No score in that receipt is a measurement**: the transport answers with a canned string, and the
judge flagging 4 of 4 rows is that string failing to parse as an SLU label, not a finding.

Engineering: `python scripts/checks/engineering_base_check.py` **PASS**;
`python scripts/checks/harness_admission_check.py` **PASS**; `ruff check` clean. The family adds
**one** pure module (`rails/slurp_intent_candidates.py`), **one** registered provider and its two
policy ids on the existing `rails.knowledge_provider` base, **one** phase program
(`phase-direct-only-supplied-v1`, `phase-direct-only-v1` with `knowledge: "supplied"`), and config
fragments — **no new adapter, controller, probe module or launcher directory**. 30 new unit tests.

---

## 11. What a flight agent must do, in order

0. **Merge this branch and re-run the gates**: `engineering_base_check.py`, `harness_admission_check.py`, `pytest`.
1. **Write the exposure row** for KU-S4N — its own run id, its own plan, `consumed = no` — before any contact.
2. **Dry run** (`--dry-run`): preflight only, no server, no contact.
3. **Wire check** (`--wire-check`) on a clean committed tree.
4. **Prompt fit**, zero generated tokens, all 1,000 rows, through the resident session's
   `/apply-template` + `/tokenize`. Worst envelope against the 8,192-token slot; a negative margin
   STOPS the mission. Pin the receipt into the fragment.
5. **4-row smoke** on the four rows the wire-check fragment already names.
6. **Fly KU-S4N**, one attempt, one seal, on a clean tree for the whole run; then **KU-S4N-t** the
   same way, on the same session.
7. **`core.scoring_batch`**, one job per complete manifest, never sharded, official-vs-port identity
   check, both scorers.
8. **One registered read**, then the KU-S4N verdict and its admission-table rows.
9. Only if KU-S4N is ADMITTED or NEUTRAL: close `SAEA-SLURP-KUS4-EXEMPLAR-PACKETS-V1`, write the
   KU-S4a/b fragments against its receipts, and repeat 1–8 for KU-S4a, KU-S4b, KU-S4c in that order.

---

## 12. What this authorizes, and what it forbids

**Authorizes**: the five arms above, on DEV-1000, at the budgets of section 8, under the rules of
section 5, in the order of section 4 — and nothing else today. It fixes the roster, the candidate
rule, the twin, the exemplar plan, the comparators, the analysis and the reporting obligations so
that flying is execution rather than design.

**Forbids**: flying KU-S4a or KU-S4b before the packet-promotion precondition of section 7 closes;
flying any cell above KU-S4N before KU-S4N and its twin have sealed and been read; any test-split
contact; any knob, k, depth or seed change on the strength of a number; pooling any two cells into
one claim; reading the fully-covered stratum as an effectiveness claim at n = 341; claiming the
modality contrast is token-matched; any superiority or generalization claim; and any Stage-3 or
paper-scale activity.
