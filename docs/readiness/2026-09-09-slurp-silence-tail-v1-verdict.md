# Verdict — the SLURP DEV-1000 closed-list arm re-flown with a 2.0 s silence tail

**NOT ADMITTED.** Run `SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1`, attempt
`attempt-20260909T035340Z-95296f`, `COMPLETED` on study commit `53d31f59`, **1,000 of 1,000 rows**,
one attempt, none aborted, **no recovery re-registration used**, `study_repo_dirt` empty. The SLURP
cell of `docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md` §§1.2, 4.1 and
6.1, flown on the owner GO recorded in its own exposure row before the first contact.

---

## 0. The answer

**Every headline number rises, and the cell is NOT ADMITTED, because §4.1 asks for more than a rise
and two of its three clauses were written to catch exactly what happened.** Intent accuracy goes
73.10 % → **74.40 %**, a paired **+1.30 pp** [+0.19, +2.43] speaker-clustered; the interval excludes
zero but its lower bound does not clear the **+0.60 pp** bar §4.1 clause 1 fixes.

| | value |
|---|---:|
| intent accuracy (scenario+action), cell | **74.40 %** |
| intent accuracy, sealed comparator `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1` | 73.10 % |
| paired delta, **speaker-clustered CI90 — the honest interval** | **+1.3000** [+0.1934, +2.4262] |
| paired delta, stratified by gold scenario | +1.3000 [+0.2000, +2.4000] |
| paired delta, equal-stratum weighting, speaker-clustered | +1.2747 [+0.2040, +2.3332] |
| SLU-F1 (official micro), cell → comparator | **37.83** vs 35.80 |
| **§4.1 clause 1 — intent CI90 lower bound > +0.60 pp** | **FAIL** (+0.1934) |
| **§4.1 clause 2 — SLU-F1, scenario and action all non-inferior at −0.60 pp** | **FAIL** (scenario −0.6921) |
| **§4.1 clause 3 — per-scenario harm bound** | **FAIL** (5 scenarios lose; worst −10.26 pp) |
| **verdict** | **NOT ADMITTED** |
| §5 prediction (0 to +2.0 pp) | **held** |

Both interval families — speaker-clustered and scenario-stratified — reach the **same verdict on all
three clauses**, so nothing here turns on which one is read as honest.

**What the number is, and what it is not.** DEV-1000 is a dev-tier optimization population and every
request carried 2.0 s of digital silence that no published system appends. This is **not a
like-for-like reproduction of any published SLURP protocol** and must never be reported as one. §8 is
what it licenses.

---

## 1. The falsifier, run before any score file was opened

**§4.4 HOLDS ON 1,000 OF 1,000 ROWS, and on 4 of 4 in the smoke.**

| check | flight | smoke |
|---|---:|---:|
| rows checked | **1,000 of 1,000** | 4 of 4 |
| delivered media SHA-256 equals the committed D1 supplement entry | **1,000** | 4 |
| delivered media SHA-256 equals the frozen runtime view's own record | **1,000** | 4 |
| delivered media byte count equals the committed entry | **1,000** | 4 |
| media path confined to the variant's own derived root | **1,000** | 4 |
| delivered seconds = sealed comparator's delivered seconds + exactly 2.0 | **1,000** | 4 |
| delivered sample count = sealed + exactly 32,000 at 16 kHz | **1,000** | 4 |
| metered seconds equal requested seconds | **1,000** | 4 |
| packet handed to the decoder equals the promoted `@ts2` packet by SHA-256 | **1,000** | 4 |
| packet id carries the `@ts2` suffix | **1,000** | 4 |
| `mmproj_loaded` false | **1,000** | 4 |
| **disagreeing rows** | **0** | **0** |
| **missing / extra rows against the roster** | **0 / 0** | **0 / 0** |

Delivered total **4,884.793688 s** against the sealed comparator's **2,884.793688 s** on the same
1,000 rows: a difference of **2,000.000000 s = 1,000 × 2.0**, and the manifest's own metered figure
to the digit. The committed supplement's SHA-256 was re-measured from its own bytes and equals the
value the dataset fragment declares (`56a75cf6…fedae1`).

**And the wire agrees, to the token.** Prompt tokens **2,216,161** against the comparator's
**2,190,161** on the same rows — a difference of **26,000 = 1,000 × 26 exactly**, with **no residue
and no other value in the histogram**: every single row is +26 and none is +25 or +27. 26 tokens is
2.0 s at this encoder's block rate, and it is the same 26 the Earnings-21 cell measured on 1,593
90-second windows. Nothing but the tail reached the core.

---

## 2. The identity gate, passed before the first contrast

§2 requires the sealed comparator to reproduce its own published numbers from its own sealed bytes,
to the digit, before any contrast is computed. It does, on all nine anchors:

| anchor | §1.2 published | reproduced |
|---|---:|---:|
| scenario | 82.60 | **82.60** |
| action | 74.60 | **74.60** |
| intent | 73.10 | **73.10** |
| entities strict | 21.91 | **21.91** |
| word-F1 | 33.69 | **33.69** |
| char-F1 | 38.20 | **38.20** |
| SLU-F1 | 35.80 | **35.80** |
| unparsed | 3 | **3** |
| port-vs-official identity check | passed | **passed** (SLU-F1 abs diff 0.0) |

Both arms were scored **once each over their complete 1,000-row manifest** through
`core.scoring_batch` with `include_per_sample=True`, one job per manifest, never sharded. Both jobs
report `verified: true`. The paper-facing scorer is `slurp-slu-official-projected-v2` — the real,
unmodified official `evaluate.py` at the pinned clone plus the legal-label projection v2 the
2026-09-06 re-lock fixed — and `slurp-slu-f1-normalized-v1` runs beside it as the secondary. Neither
scorer is declared by the sealed manifests, so **one derived manifest per arm** was written beside
each sealed one, differing from it in the `scorers` list and in nothing else; the sealed manifests
were not touched and their SHA-256s are in the receipt.

---

## 3. The numbers

### 3.1 The official projected-v2 aggregates, n = 1,000

| metric | comparator | cell | delta |
|---|---:|---:|---:|
| scenario accuracy | 82.60 | 82.90 | +0.30 |
| action accuracy | 74.60 | 75.60 | +1.00 |
| **intent accuracy** | **73.10** | **74.40** | **+1.30** |
| entities strict F1 | 21.91 | 24.36 | +2.45 |
| word-F1 | 33.69 | 35.77 | +2.08 |
| char-F1 | 38.20 | 40.15 | +1.95 |
| **SLU-F1 (micro)** | **35.80** | **37.83** | **+2.03** |
| unparsed | 3 | 3 | 0 |

**Every one of them moves up, and the unparsed count does not move at all.** Whatever the tail did,
it did not buy accuracy by trading away parseability.

### 3.2 The paired contrasts, per row on the published key

Signed cell − comparator; 10,000 replicates, seed 20260903, CI90. The entity columns are the mean of
the official **per-row** F1, which is what a paired contrast can be computed on; the paper-facing
SLU-F1 is the micro aggregate of §3.1.

| metric | comparator | cell | delta | speaker-clustered CI90 | scenario-stratified CI90 | saves | harms | ties | sign p |
|---|---:|---:|---:|---|---|---:|---:|---:|---:|
| **intent** | 73.100 | 74.400 | **+1.3000** | **[+0.1934, +2.4262]** | [+0.2000, +2.4000] | 29 | 16 | 955 | 0.0724 |
| scenario | 82.600 | 82.900 | +0.3000 | [−0.6921, +1.4085] | [−0.7000, +1.3000] | 19 | 16 | 965 | 0.7359 |
| action | 74.600 | 75.600 | +1.0000 | [−0.0987, +2.1102] | [−0.2000, +2.2000] | 30 | 20 | 950 | 0.2026 |
| entities strict F1 (per row) | 12.959 | 14.347 | +1.3881 | [+0.2780, +2.5205] | [+0.3666, +2.4333] | 40 | 22 | 938 | 0.0300 |
| word-F1 (per row) | 18.872 | 20.181 | +1.3098 | [+0.2046, +2.4877] | [+0.2899, +2.3612] | 76 | 46 | 878 | 0.0084 |
| char-F1 (per row) | 21.127 | 22.357 | +1.2294 | [+0.0456, +2.4606] | [+0.1251, +2.3734] | 80 | 47 | 873 | 0.0043 |
| SLU-F1 (per row) | 19.746 | 21.031 | +1.2848 | [+0.1455, +2.4788] | [+0.2234, +2.3489] | 79 | 49 | 872 | 0.0101 |

**Both weightings, and they agree.** The equal-stratum weighting — the unweighted mean over the 18
gold scenarios of each scenario's own mean per-row delta — puts intent at **+1.2747**
[+0.2040, +2.3332] speaker-clustered and [+0.1312, +2.4271] scenario-stratified, against the
natural-mixture **+1.3000**. Nothing in this cell depends on the scenario mixture.

**The pairing structure.** 1,000 paired rows, 18 gold scenarios, **124 speaker clusters** (largest
55 rows, median 6). Speaker clusters and scenario strata cannot be crossed on this carrier — a SLURP
speaker records across scenarios, so no cluster sits inside one stratum — which is why the two
families are reported side by side rather than combined, exactly as Earnings-21 reports its
call-clustered interval beside its stratified one.

### 3.3 The secondary scorer agrees in sign on every metric

`slurp-slu-f1-normalized-v1` applies the pinned slot normalizer to gold and prediction alike
(2 false merges on this corpus, reported whether zero or not). Micro SLU-F1 **36.43 → 38.52**.

| metric | official delta | normalized delta | same sign |
|---|---:|---:|---|
| intent | +1.3000 | +1.4000 | yes |
| scenario | +0.3000 | +0.8000 | yes |
| action | +1.0000 | +1.2000 | yes |
| entities strict F1 (per row) | +1.3881 | +1.5386 | yes |
| word-F1 (per row) | +1.3098 | +1.3173 | yes |
| char-F1 (per row) | +1.2294 | +1.2515 | yes |
| SLU-F1 (per row) | +1.2848 | +1.3000 | yes |

**Seven of seven.** The secondary's own intent interval is [+0.2783, +2.5748] speaker-clustered,
which also fails clause 1's +0.60 bar. The verdict does not change under the normalizer.

---

## 4. §4.1, quoted before it is applied

> **ADMITTED** as a model-usage local optimization **iff all three hold**:
>
> 1. **Intent accuracy (scenario+action), the paper-facing headline.** The CI90 lower bound on the
>    delta is **> +0.60 pp** — above zero and above the imported null margin. Point estimate positive.
> 2. **SLU-F1 does not worsen.** Its CI90 lower bound is above **−0.60 pp** (non-inferiority at the
>    same imported margin), and scenario and action accuracy are both non-inferior on the same rule.
> 3. **No stratum is harmed beyond the carrier's own rule.** SLURP's per-scenario harm bound, as
>    EVO-S1 already uses it: no scenario loses more than **3.0 pp** of intent accuracy, and at most
>    **2 of the 18** scenarios lose anything at all.

**Clause 1 — FAIL.** Point estimate positive (+1.3000) and the interval excludes zero, but the CI90
lower bound is **+0.1934** speaker-clustered and **+0.2000** stratified. Neither is above +0.60. The
clause is missed by roughly 0.4 pp of lower bound, not by direction.

**Clause 2 — FAIL, and narrowly, on scenario.** SLU-F1's lower bound is **+0.1455** (comfortably
above −0.60) and action's is **−0.0987** (also above), but **scenario accuracy's lower bound is
−0.6921**, which is *below* −0.60 by 0.09 pp. Scenario accuracy is the metric the tail moved least
(+0.30, 19 saves against 16 harms, sign-test p 0.74) and its interval is therefore the widest
relative to its point estimate. Under the equal-stratum weighting the same clause fails wider
(scenario [−0.8810, +1.2576]). This is the clause failing on **imprecision**, not on measured harm.

**Clause 3 — FAIL, and not narrowly.** The rule allows at most 2 of 18 scenarios to lose anything
and none to lose more than 3.0 pp. Measured: **5 scenarios lose intent**, and the worst loses
**10.26 pp**.

| scenario | n | comparator | cell | delta | saves | harms |
|---|---:|---:|---:|---:|---:|---:|
| `takeaway` | 39 | 76.92 | 66.67 | **−10.2564** | 0 | 4 |
| `recommendation` | 60 | 71.67 | 68.33 | −3.3333 | 0 | 2 |
| `iot` | 61 | 85.25 | 81.97 | −3.2787 | 1 | 3 |
| `music` | 51 | 84.31 | 82.35 | −1.9608 | 1 | 2 |
| `news` | 60 | 78.33 | 76.67 | −1.6667 | 0 | 1 |

The full 18-row table is `docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-silence-tail-v1/verdict/per-scenario-table.md`.
On the other side, `general` gains **+8.20 pp**, `audio` +6.67, `datetime` +6.56, `cooking` +5.41 and
`calendar` +4.92; three scenarios are exactly flat. **The tail is not a uniform improvement — it is a
redistribution with a positive sum**, and clause 3 exists to say that a redistribution is not a local
optimization you may switch on for everybody.

**Verdict: NOT ADMITTED**, on all three clauses, under both interval families.

---

## 5. The null this verdict used, and it was imported

§3 is explicit: **no same-request null has been measured on SLURP.** The margin this verdict applies
— ±0.60 pp — is §4.1's own figure, taken from the Earnings-22 same-request null's half-width on the
same scale. **It is imported, not measured**, and this note says so where it uses it.

§3's second consequence does **not** fire here. A result *inside* the imported margin is "NOT
ADMITTED and NOT REFUTED". This result is not inside it: the intent interval
[+0.1934, +2.4262] excludes zero and sits mostly above +0.60. What failed is that its **lower bound**
does not clear +0.60 — an imprecision failure against an imported bar, not a null result.

**That makes the named next cell concrete, and §3 already named it: measure this carrier's own
same-request null.** Until that exists, no one can say whether a +1.30 pp intent movement on 1,000
SLURP rows is one null half-width or six. Earnings-21 has since measured its own null
(`SAEA-E21-FULL44-NULL-REPLICATE-V1`); SLURP has not, and every SLURP margin in this study is
borrowed until it does.

---

## 6. Cost, throughput and the serving session

| | |
|---|---:|
| calls | **1,000 of 1,050** registered |
| speech audio seconds | **4,884.7937 of 5,000** registered |
| contact window | 247.30 s = **0.0687 GPU-h of 0.30** registered |
| throughput | **242.6 rows/min**, 4.04 rows/s |
| prompt tokens / completion tokens | 2,216,161 / 26,215 |
| paid API spend | **0** |

**The flight attached and never started or stopped a server.** It bound the coordinator's resident
session `slurp-np8-ts2-c65536-20260909` (8 slots × 8,192, `-c 65536 -np 8`, port 8080,
`LLAMA_SPEECH_FEATURE_ROOT` on the `@ts2` packet root) through `core.session.attach_session`, and the
session was still live with all 8 slots idle afterwards.

Monitor summary over the flight's own contact window (22 samples at 10 s): **mean GPU utilization
78.86 %**, mean power 86.32 W, peak 88.17 W, **parked fraction 0.0** — the card was never idle inside
the window. Host free memory bottomed at 26.14 GB and WSL available at 40.17 GB, nowhere near the
kill hazard. The smoke's own contact window was 4.08 s and fell entirely **between** two monitor
samples, so its window summary carries zero samples; that is recorded rather than filled in.

---

## 7. The re-lock consequence — which does NOT fire

Had this cell been ADMITTED, the consequence was fixed in advance: the SLURP direct comparator would
move to the `@ts2` media, and **every pending SLURP cell — the KV slot-knowledge-view family, KU-S3,
KU-S4 and the logprob judge probe — would have had to be READ against the new comparator** (read,
never re-run).

**It is NOT ADMITTED, so the comparator does not move.** `SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1`
at intent **73.10** / SLU-F1 **35.80** under `slurp-slu-official-projected-v2` remains the SLURP
comparator, and every pending SLURP cell keeps reading against it, unchanged. No pending cell is
invalidated, none is re-run, and nothing in the SLURP ladder moves because of this cell.

---

## 8. What this cell licenses, and what it cannot conclude

**It licenses one thing: a measured, signed answer to the transfer question.** The 2.0 s tail
transfers to SLURP as a **positive but sub-threshold, unevenly distributed** effect — the pooled
direction is the Earnings-22 direction, the size is inside §5's signed prediction, and the
distribution is what blocks it.

It cannot conclude:

* **Nothing about the SLURP `test` split or FINAL60.** Neither is touched; `test_split_read` is
  FALSE.
* **No like-for-like comparison against any published SLURP number.** DEV-1000 is dev-tier and the
  media is not the published media.
* **Nothing about generalization or superiority**, and nothing that belongs to Stage-3.
* **Not that the tail is the last difference, and not that the encoder pad was removed**: appending
  whole mel blocks leaves the residue `(n_samples // 160) % 100` unchanged, so the same padded block
  is still sent, two seconds later.
* **Not that a result on this carrier predicts another.** There is no cross-carrier verdict: three
  cells, three answers, side by side. Earnings-21 was NOT ADMITTED for a different reason
  (`docs/readiness/2026-09-07-e21-full44-tail2s-v1-verdict.md`); Audio2Tool has not flown.

### 8.1 The two named next cells, in order

1. **The SLURP same-request null**, and it is now the blocking one. §3 named it before this cell
   existed and this result is exactly the case it was named for: an effect whose direction is clear
   and whose size cannot be judged against a borrowed bar. Without it, clause 1's +0.60 will keep
   deciding SLURP cells on an Earnings-22 number.
2. **The `takeaway` and `iot` regression**, which is a mechanism question rather than a statistical
   one: 4 of 39 `takeaway` rows and 3 of 61 `iot` rows flipped from correct to wrong with two seconds
   of silence appended and nothing else changed. That is a small, enumerable set of rows whose
   sealed outputs both arms already carry.

---

## 9. Receipt

`docs/checks/speech-aware-evidence-acquisition/2026-09-09-slurp-silence-tail-v1/`, with
`MANIFEST.sha256` over every file:

| path | what |
|---|---|
| `read.py` | the archived copy of the single registered read: the score batch, the identity gate, both interval families, both weightings, the secondary and the §4.1 decision. Scoring-side only, zero contacts |
| `falsifier.py` | the archived copy of the §4.4 media falsifier, run on both populations before any score file was opened |
| `build_result_summary.py` | the assembler; reads nothing but `verdict/read.json` |
| `smoke-4/` | the §8 item 5 smoke: its falsifier, flight receipt and monitor window. **Carries no metric** |
| `flight-1000/` | the flight: the 1,000-row falsifier, the flight receipt, the monitor window over the contact window |
| `verdict/read.json` | the full read — every aggregate, every interval, the per-scenario tables, both weightings, the secondary |
| `verdict/result-summary.json` | the machine form of this verdict |
| `verdict/per-scenario-table.md` | all 18 gold scenarios with intent and SLU-F1 deltas |
| `verdict/batch-summary.json` | the verified `core.scoring_batch` record: one job per manifest, `include_per_sample`, never sharded |

Exposure rows: `SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-SMOKE-V1` and
`SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1`, both registered and committed before their first contact.
Harness-admission entry: `docs/receipts/harness-admission.json`, module *silence tail on the
delivered clip*, carrier `slurp`, status **HARMFUL** under the table's own definition (a gating guard
failed), blocked from every default plan, with its provisional obligation UNMET because the switch
form this table records has never been flown on this carrier.
