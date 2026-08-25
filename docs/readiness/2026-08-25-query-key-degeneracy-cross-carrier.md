# CROSS-CARRIER QUERY-KEY DEGENERACY — the constant key is an AUDIO2TOOL
# pathology, not a general one; SLURP's keys repeat because LABELS COLLIDE

Date: 2026-08-25. Status: **MEASUREMENT — computed, ZERO CONTACTS, the A2T control
reproduced exactly and both SLURP gates passed.**
Row `SAEA-SN-MF-QUERY-KEY-DEGENERACY-CROSS-CARRIER` (registered `0bdfeb27`, **before any
computation**).
Module `src/speech_aware_evidence_acquisition/analysis/query_key_degeneracy_cross_carrier.py`.
Receipt `docs/checks/speech-aware-evidence-acquisition/2026-08-25-query-key-degeneracy/degeneracy-report.json`
(sha256 `a1a40999dfddae7642cdc3eaa6763a8fcffe1874e5488210e41618c219a6aeae`).

**Spend: 0 frozen-core contacts, 0 embedding-tool contacts, 0 tokenizer contacts, 0 audio
seconds, 0.0 GPU hours, 0 new dependencies.** The offline guard
(`analysis.dev100_reviewer_audit.arm_offline_guard`) was armed before the first input was opened
and recorded **0 outbound connection attempts against 0 targets**. The resident llama-server on
port 8090 (pid 38623) was never contacted, probed, reconfigured or stopped. Wall 332.2 s. No knob
was changed; `configs/`, `rails/` and `core/` were not written. New code landed only under
`analysis/`.

**Reading tier.** The SLURP **unexposed NEW500** is the locked baseline's own population. Every
statistic this document computes on it is a **SECONDARY READING**, labelled as such in every table,
and it **must not be used to revise, re-tune or restate the lock**. The nested prior-exposed
DEV-500 half and the A2T-G1-104 are exposed-tier and carry the exposed secondary-reading caveat at
every citation.

---

## 0. The answer in one paragraph

**The A2T control reproduces exactly, and SLURP does not carry the A2T pathology.** On Audio2Tool
the 15 dead-direct trajectories carry **5 distinct query vectors** (0.333 per trajectory), **11
share one key**, that one key produced **one supply**, and the 89 label-recovered trajectories
carry **84** distinct keys (0.944) — every figure reproduced from the sealed artifacts with **0
disagreements** against the landed diagnosis. On SLURP DEV-1000 the dead-direct subgroups carry
**136 distinct keys of 160** (0.850, unexposed) and **122 of 166** (0.735, exposed), so by the
pre-registered absolute clause (≥ 0.90) **both SLURP halves fall below the bar and the clause
fires** — and that is reported first, because it is what was registered. But the same registration
fixed three discriminants, and all three say the mechanism is different. **DIRECTION:** on A2T the
α veto selects the degenerate subset (dead/live degeneracy ratio **0.353**); on SLURP it selects
the *more* diverse subset (**1.240** unexposed, **1.027** exposed) — the veto does not concentrate
key collapse on the dispatching set at all. **CONTENT:** A2T's dead-direct answers are
**14/15 = 93.3 %** structurally empty, median **0** distinct content tokens, median length **2
characters**; SLURP's are **2/160 = 1.25 %** and **3/166 = 1.81 %** structurally empty, median
**9** distinct tokens, median length **102 / 99.5 characters** — a **74.7× / 51.6×** difference in
emptiness. **EXTENT:** A2T's largest identical-key cluster holds **73.3 %** of its dead-direct
group; SLURP's holds **8.1 % / 11.5 %** (**9.0× / 6.4×** smaller). The claim under test —
*"SLURP's dead-direct answer is a wrong label that still carries utterance content, so its query
stays informative; A2T's is an empty call that carries none"* — is **CONFIRMED and quantified**:
**98.75 % / 98.19 %** of SLURP dead-direct answers name a scenario/action pair (139/160 and
143/166 an out-of-vocabulary pair, 19/160 and 20/166 swap-recoverable). SLURP's keys repeat
because **short labels COLLIDE**, not because answers are empty, and the proof that this is
benign collision rather than pathology is that it happens **more** in the healthy label-recovered
group. The τ consequence follows: on A2T **9 of 15** dead-direct gold facets sit below τ = 0.65
(band 0.5653–0.6356, median position 83); on SLURP **10 of 160 (6.25 %)** and **14 of 166
(8.43 %)** do, and the dead-direct **median gold-facet position is 1** on both halves. **The τ gate
is the binding stage on A2T's dead-direct set and is essentially not binding on SLURP's.**

---

## 1. Provenance and gates — nothing below was read until these passed

### 1.1 The A2T control is a STOP CONDITION, and it passed

The registration fixed it before the module ran: if the recomputed A2T degeneracy did not
reproduce the landed diagnosis, this row reports the discrepancy and does **not** proceed to the
SLURP measurement. `run()` raises on that path. It did not raise.

| A2T fidelity gate (`a2t_control.fidelity_gate`) | result |
|---|---|
| replayed supply = flown per-sample supply | **104 / 104**, 0 mismatch ids |
| replayed dispatch decision = flown decision | **104 / 104**, 0 mismatch ids |
| replayed direct-label recovery = flown | **104 / 104**, 0 mismatch ids |
| trajectories with empty recall / empty supply | **0 / 0** |
| dead-direct set **is** the flown dispatched set | **yes** (asserted, `run()` raises otherwise) |

### 1.2 The SLURP gates

| SLURP gate | result |
|---|---|
| flown direct-decode text re-hashes to the digest its own landed query-vector record carries (`k1.assert_query_text_identity`) | **1000 / 1000** |
| committed byte pins on the DEV-1000 BLEND report / outputs / mechanical record (`k1.assert_dev1000_byte_pins`) | **3 / 3 verified** |
| replayed supply = flown supply on every dispatched trajectory | **340 / 340**, 0 mismatches |
| replayed retain/dispatch decision = flown contact count | 986 / 1000 |
| the 10 mismatches are all v2 retain-override fires | **yes**, 0 unexplained (14 override fires in the population) |
| v2 override fires on a **dead-direct** trajectory | **0** — asserted; `run()` raises otherwise |
| vectorised recall vs `kb.multidim_recall` probes / `kb_policy._cosine` probes | 8 / **9000** |

The v2 deviation is proved, not tolerated. The DEV-1000 BLEND arm flew the δ ≥ 0.14 retain-override
that the lock read falsified out of sample; the v1 replay therefore disagrees with the flown contact
count on exactly the override fires. **The override requires a RECOVERED direct label to disagree
with, so it can never fire on a dead-direct trajectory** — this row asserts that empirically (0 of
14 fires land on a dead-direct sample) rather than arguing it, which is what makes the
dead-direct / label-recovered partition below independent of the v2 knob.

### 1.3 The retrieval key IS the contact-0 answer, byte for byte

The content-dimension query vector is the embedding of the trajectory's **own** contact-0 answer
text. This is not assumed on either carrier: on A2T each landed Pass-A text is re-hashed against
the `text_sha256` its own landed query-vector record carries (`ccd.load_a2t_attempt4`), and on
SLURP the same identity is proved on **1000 of 1000** samples through
`k1.assert_query_text_identity`. When the answer is literally the same string, the key is the
same vector — that is the whole mechanism under study.

### 1.4 Artifact hashes

| artifact | sha256 |
|---|---|
| A2T knowledge snapshot | `ec2f9ec454d3f16957ac08e4d7686a6f3941f22c600ff2b1b2b97ff43baf9fb2` |
| A2T content-facet NPZ | `00a7ebe9b8325ffc2c7b8e45ac4f0c8475b2d3e76994cc0f539f7b5ad5740f45` |
| A2T sealed Pass-A direct outputs | `73e28511f419cd67b1721d829438f8c102e725e01243c9a9f000e00d92aadc9c` |
| A2T sealed attempt-4 BLEND answers | `24a7864263226f4918076571aee359d40ee76838f9cea1da2bbae38f6b6bdd18` |
| A2T sealed attempt-4 mechanical record | `59458c491368a117721041e4ba1538549f3e1e28bdb342e4927703ad5892644e` |
| **A2T sealed attempt-4 query vectors** | `2915aa0e4c690fc612777f28c88949956b2cfb108582c4e40eaca36e6a184be7` |
| A2T sealed M0 answers | `dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467` |
| SLURP knowledge snapshot | `e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57` |
| SLURP content-facet NPZ | `0bcb955a3a0ab84880f0d039ae702e77d1247ed23c3b8cecb468cbb1e0221c72` |
| SLURP DEV-1000 BLEND sealed outputs | `542a029adca8fb8daf3618e8a049aecdba1b04aba30eafedb67099fb6e08cf14` |
| SLURP DEV-1000 BLEND sealed mechanical record | `e55b6632d85a0037fb928d565fb2ef1b40c987c915dd98a9f2599d78113c828e` |
| SLURP DEV-1000 run trace | `598780deb9ddb98842e503871206ef4afc33619c49162ae626f2858fa356d6df` |
| **SLURP DEV-1000 BLEND query vectors** (`query-vectors.jsonl`) | `efcf948918e1b4f6c695998da21311d1fa766de57dbd84feedce5ae5ade11702` |
| SLURP DEV-1000 BLEND committed mechanical report | `c3ed01699a43087e719b917c751d1ce96d6b0992107d58437fc048fd12ba5930` |

**SLURP's query vectors WERE persisted.** They are in the BLEND attempt directory
`$SPEECHRL_DATA_DIR/runs/SAEA-DEV1000-BASELINE-LOCK/attempt-20260825T054707Z-dev1000blend/query-vectors.jsonl`
(22.9 MB, 1,000 `query:<sample_id>` records with `values` and `text_sha256`), exactly as the A2T
run stored them. **The M0 attempt has none, and correctly so**: M0 is the single-contact baseline
arm — it never embeds an answer, so it has no retrieval query. Every query vector in this document
is the BLEND arm's, which is the only arm that has one.

Frozen cell, identical on both carriers: α = 0.45, **τ = 0.65**, m = 5, c = 2, `top_l` = 3,
`top_k` = 5, weights (0.5 / 0.3 / 0.2).

---

## 2. Q1 — the A2T control, REPRODUCED with 0 disagreements

`a2t_control.recomputed` against `a2t_control.landed_reference`
(`docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md` §4.1, receipt sha256
`64327e98…9a3e14`):

| quantity | landed diagnosis | recomputed here | agree |
|---|---|---|---|
| dead-direct n | 15 | **15** | ✔ |
| dead-direct distinct query vectors | 5 | **5** | ✔ |
| dead-direct distinct contact-0 texts | 5 | **5** | ✔ |
| dead-direct largest identical-key cluster | 11 | **11** | ✔ |
| label-recovered n | 89 | **89** | ✔ |
| label-recovered distinct query vectors | 84 | **84** | ✔ |
| label-recovered distinct contact-0 texts | 84 | **84** | ✔ |
| distinct flown supplies inside the 11-cluster | 1 | **1** | ✔ |

`control_reproduced = true`, `disagreements = {}`.

**And the distinct-supply count on the whole A2T dead-direct set, which the diagnosis did not
publish:** the 15 dead-direct trajectories received **5 distinct flown supplies** — 0.333 per
trajectory, the same ratio as their keys, with the **largest identical supply covering 11 of 15**.
One key, one supply, eleven times over.

The A2T retrieval profile also reproduces exactly: dead-direct gold-in-top-5 **4/15 = 26.67 %**,
median gold-facet cosine **0.6054**, median gold-facet position **83**; label-recovered **64/89 =
71.91 %**, **0.8632**, position **1**. Deficit **−45.2434 pp** and **−0.257802**.

> **The control holds. Everything below is licensed.**

---

## 3. Q2 — the degeneracy table on both SLURP halves

Partition: **dead-direct** = `kb_policy.default_label_normalizer` returned `None` on the flown
direct-decode text — the same predicate the A2T side uses (`a2t_label_normalizer` returning
`None`) and the same one `analysis.dev100_next_experiment_projections` has used since the A3/A4
projections. **label-recovered** = everything else.

### 3.1 SLURP DEV-1000 **UNEXPOSED NEW500** — ⚠ **SECONDARY READING** ⚠

*These statistics are descriptive. They must not revise, re-tune or restate the locked baseline.*

Dead-direct **160 of 500 (32.0 %)**; partition: **oov-pair 139, swap-recoverable 19, no-fields 2**.
(The A2T diagnosis §7.2 clause I1 named this subgroup as "n = 160"; that figure is **confirmed
here** by direct computation.)

| statistic | dead-direct (n = 160) | label-recovered (n = 340) |
|---|---|---|
| **distinct query vectors / trajectories** | **136 / 160 = 0.850** | **233 / 340 = 0.685** |
| distinct contact-0 texts / trajectories | 133 / 160 = 0.831 | 217 / 340 = 0.638 |
| **largest identical-key cluster** | **13 (8.13 %)** | **24 (7.06 %)** |
| **distinct supplies / trajectories** | **125 / 160 = 0.781** | 196 / 340 = 0.576 |
| distinct supplies inside the largest key cluster | 1 | 1 |
| **gold-in-top-5** | **112 / 160 = 70.00 %** | **260 / 340 = 76.47 %** |
| **median gold-facet cosine** | **0.800468** | **0.834870** |
| median gold-facet position | **1** | **1** |
| structurally empty contact-0 answers | **2 / 160 = 1.25 %** | 0 / 340 = 0.00 % |
| median distinct tokens per contact-0 answer | 9 | 9 |
| median tokens outside the group's modal text | 5.5 | 5.5 |
| median contact-0 answer length | 102 chars | 99 chars |

Retrieval deficit on this half: **−6.4706 pp** and **−0.034402** median cosine — inside the
−4.0 to −7.9 pp band the key-construction plan §2.2 quotes from other populations.

### 3.2 SLURP DEV-1000 **prior-exposed nested DEV-500** (exposed tier)

Dead-direct **166 of 500 (33.2 %)**; partition: **oov-pair 143, swap-recoverable 20, no-fields 3**.

| statistic | dead-direct (n = 166) | label-recovered (n = 334) |
|---|---|---|
| **distinct query vectors / trajectories** | **122 / 166 = 0.735** | **239 / 334 = 0.716** |
| distinct contact-0 texts / trajectories | 117 / 166 = 0.705 | 214 / 334 = 0.641 |
| **largest identical-key cluster** | **19 (11.45 %)** | **17 (5.09 %)** |
| **distinct supplies / trajectories** | **112 / 166 = 0.675** | 204 / 334 = 0.611 |
| distinct supplies inside the largest key cluster | 1 | 1 |
| **gold-in-top-5** | **116 / 166 = 69.88 %** | **252 / 334 = 75.45 %** |
| **median gold-facet cosine** | **0.772120** | **0.839903** |
| median gold-facet position | **1** | **1** |
| structurally empty contact-0 answers | **3 / 166 = 1.81 %** | 0 / 334 = 0.00 % |
| median distinct tokens per contact-0 answer | 9 | 9 |
| median tokens outside the group's modal text | 5.0 | 5.0 |
| median contact-0 answer length | 99.5 chars | 99 chars |

Retrieval deficit on this half: **−5.5696 pp** and **−0.067783** median cosine.

### 3.3 Two measurement caveats, stated rather than buried

1. **The distinct-supply statistic is defined differently on the two carriers, by necessity.** On
   A2T the counts are the **FLOWN** supply, which is what the landed diagnosis counted — and the
   A2T flight records `fusion_selected_value_ids` only for a trajectory it **dispatched**, so all
   89 label-recovered trajectories carry the empty tuple. **The A2T label-recovered supply column
   is null by construction and is not a degeneracy**; only its dead-direct supply column is
   meaningful. On SLURP the counts are the **REPLAYED** fusion decision, which the frozen fuser
   produces on every trajectory, so the statistic is defined identically on both SLURP groups.
   The receipt cross-checks it: `dead_direct_flown_supply_cross_check` recounts the SLURP
   dead-direct statistic on the **flown** supply over the dispatched members and returns the
   identical block (125/160 and 112/166), and the flight gate has already proved replayed = flown
   on 340 of 340 dispatched trajectories.
2. **On SLURP the embedding is not a pure function of its input text; on A2T it is.** Measured:
   SLURP dead-direct 136 distinct vectors from 133 distinct texts (+3), label-recovered 233 from
   217 (+16), exposed 122 from 117 (+5) and 239 from 214 (+25). A2T: 5 from 5 and 84 from 84 (+0).
   Identical SLURP texts were therefore embedded to slightly different vectors — the flight
   embedded one contact per sample and float results are not bit-stable across batch composition.
   **Consequence for this document: on SLURP the distinct-TEXT ratio is the conservative floor on
   key diversity, and it is still 0.831 / 0.705 against A2T's 0.333.** No conclusion here depends
   on the vector-vs-text difference, and both counts are published in every block.

---

## 4. Q3 — the verdict, and the evidence rather than the story

### 4.1 The pre-registered clause fires, and is reported first

The registration fixed the A2T diagnosis's degeneracy clause — **distinct query vectors per
trajectory ≥ 0.90** — as the decision rule, and fixed that the outcome is reported whichever way
it comes out. **Outcome: SLURP's dead-direct subgroup is BELOW 0.90 on both halves** (0.850 and
0.735). Taken as a bare threshold, that reads "SLURP degenerates too".

### 4.2 The same registration fixed three discriminants, and all three say otherwise

A one-sided absolute threshold cannot, by construction, tell *"the key is shared because the
answer was empty"* apart from *"the key is shared because two utterances genuinely carry the same
short label"*. The three quantities that can were fixed in the same registration:

| discriminant | A2T (n = 15 / 89) | SLURP unexposed (160 / 340) | SLURP exposed (166 / 334) |
|---|---|---|---|
| **D-I DIRECTION** — dead/live degeneracy ratio | **0.353** | **1.240** | **1.027** |
| does the α veto concentrate key collapse on the dispatching subset? | **YES** | **NO** | **NO** |
| **D-II CONTENT** — dead-direct structurally empty answers | **93.33 %** | **1.25 %** | **1.81 %** |
| median distinct tokens per dead-direct answer | **0** | **9** | **9** |
| median tokens outside the group's modal text | **0** | **5.5** | **5.0** |
| median dead-direct answer length | **2 chars** | **102 chars** | **99.5 chars** |
| **D-III EXTENT** — largest key cluster's share of the group | **73.33 %** | **8.13 %** | **11.45 %** |
| distinct supplies per dead-direct trajectory | **0.333** | **0.781** | **0.675** |

⚠ The unexposed column is a **SECONDARY READING**. ⚠

**D-I is decisive.** On Audio2Tool the α veto selects the degenerate subset: its dead-direct keys
are **2.83× less diverse** than its label-recovered keys, which is exactly what "ceiling B is
caused by ceiling A" means mechanically. On SLURP the ratio is **above 1 on both halves** — the
dead-direct subgroup's keys are *more* diverse than the label-recovered subgroup's. **The α veto on
SLURP does not concentrate key collapse on the dispatching set; it selects away from it.** No
threshold reading survives that.

**D-II is the causal content.** The claim under test is **CONFIRMED**: SLURP's dead-direct answer
is a wrong label that still carries utterance content. **98.75 %** (158/160) and **98.19 %**
(163/166) of SLURP dead-direct answers name a scenario/action pair — 139 and 143 of them an
out-of-vocabulary pair (two real words that are not a TRAIN intent in either order), 19 and 20
swap-recoverable (the right two words in the wrong slots). Only **2** and **3** produce no fields
at all. On A2T, **14 of 15** dead-direct answers are structurally empty tool calls, **11 of them
the identical 2-character string**, with a median of **zero** distinct content tokens. The
emptiness ratio between the carriers is **74.7×** (unexposed) and **51.6×** (exposed).

**D-III is the extent.** A2T's single largest key holds **73.3 %** of its dead-direct group and
delivered one supply to all 11 members. SLURP's largest key holds **8.1 %** and **11.5 %** —
**9.0×** and **6.4×** smaller — and each such cluster likewise received one supply, which is simply
what identical keys do.

### 4.3 What SLURP's key repetition actually is

**Label collision, not information loss.** SLURP's contact-0 answer is a short structured label;
two different utterances that the core maps to the same intent with no entities emit the same JSON
string, and identical strings embed to (nearly) identical vectors. The proof that this is benign
collision rather than pathology is in the table above: **it happens MORE in the label-recovered
group** — 0.685 and 0.716 distinct keys per trajectory, against the dead-direct group's 0.850 and
0.735 — and the label-recovered group is by construction the one whose answer named a real TRAIN
intent, i.e. the healthy one. A statistic that is *worse* on the healthy subgroup is not measuring
a pathology.

### 4.4 The cross-carrier magnitude gap, explained causally

| quantity | A2T | SLURP unexposed | SLURP exposed | A2T / SLURP |
|---|---|---|---|---|
| dead-direct retrieval deficit, gold-in-top-5 | **−45.2434 pp** | −6.4706 pp | −5.5696 pp | **6.99× / 8.12×** |
| dead-direct retrieval deficit, median gold-facet cosine | **−0.257802** | −0.034402 | −0.067783 | **7.49× / 3.80×** |
| dead-direct structurally empty answer rate | **93.33 %** | 1.25 % | 1.81 % | **74.7× / 51.6×** |
| dead/live degeneracy ratio | **0.353** | 1.240 | 1.027 | — |

**The mechanism is general; its trigger and its extent are not.** Identical keys always produce
identical supplies — that is arithmetic and holds on both carriers. What is Audio2Tool-specific is
(a) that the shared key is an **empty** answer carrying no utterance information at all, and (b)
that the α veto **selects for exactly those trajectories**, because the veto's predicate ("the
answer named no in-vocabulary target") is almost the same predicate as "the answer was empty" on
that carrier — 14 of 15. On SLURP the veto's predicate fires on answers that name the *wrong*
pair, which is a completely different failure: the answer is wrong but not empty, so its key still
points somewhere utterance-specific. That is why A2T's deficit is 7–8× SLURP's rather than equal
to it, and it is why the compounding of the two ceilings that the A2T diagnosis found **does not
transfer to SLURP as a causal chain**.

**What this row does NOT establish** is a positive account of SLURP's remaining −5.6 to −6.5 pp
deficit. Ruling out key collapse does not identify the replacement. The obvious candidate — the
answer names the wrong intent, so an informative key points at the wrong neighbourhood — is
**consistent with everything measured here and is not measured here**, because separating "the
answer text was a bad key" from "the sample was intrinsically harder, which is why the answer was
off-vocabulary in the first place" needs a manipulation this row may not perform. That confound is
already on record in `dev100_next_experiment_projections`'s own `confound_stated` field and is
carried forward unresolved.

---

## 5. Q4 — the τ-distance distributions

τ = 0.65 on both carriers, from the same frozen cell. **Observed distributions only.**

| | A2T dead-direct (15) | A2T label-recovered (89) | SLURP unexp. dead (160) ⚠ | SLURP unexp. live (340) ⚠ | SLURP exp. dead (166) | SLURP exp. live (334) |
|---|---|---|---|---|---|---|
| gold facet **below** τ | **9 (60.00 %)** | 1 (1.12 %) | **10 (6.25 %)** | 12 (3.53 %) | **14 (8.43 %)** | 13 (3.89 %) |
| below-τ cosine min | **0.565332** | 0.614296 | 0.530415 | 0.421514 | 0.491367 | 0.550548 |
| below-τ cosine median | 0.584205 | 0.614296 | 0.599251 | 0.624011 | 0.627385 | 0.603442 |
| below-τ cosine max | **0.635625** | 0.614296 | 0.649000 | 0.645218 | 0.647878 | 0.648711 |
| gap to τ, min | 0.014375 | 0.035704 | 0.001000 | 0.004782 | 0.002122 | 0.001289 |
| gap to τ, median | **0.065795** | 0.035704 | 0.050749 | 0.025989 | 0.022615 | 0.046558 |
| gap to τ, max | 0.084668 | 0.035704 | 0.119585 | 0.228486 | 0.158633 | 0.099452 |
| gap ≤ 0.05 | 2 | 1 | 5 | 9 | 11 | 8 |
| gap ≤ 0.10 | **9 (all)** | 1 | 8 | 10 | 13 | 13 |
| **median gold-facet position** | **83** | 1 | **1** | 1 | **1** | 1 |

⚠ SECONDARY READING on the two unexposed columns. ⚠

The A2T band **0.565332–0.635625** reproduces the landed diagnosis's "9 of the 11 sit at
0.5653–0.6356" exactly (the 4 gold-bearing dead-direct trajectories all pass τ, so "9 of 15 below
τ" and "9 of the 11 gold-absent" are the same nine).

**The reading.** On Audio2Tool the τ gate refuses the gold facet on **60 %** of the dead-direct
set, every one of those nine sits within 0.085 of the bar, and the median gold-facet position is
**83** — the signature of a constant key producing one fixed neighbourhood whose best cosines top
out around 0.77. **On SLURP the τ gate refuses it on 6.25 % / 8.43 %, and the dead-direct median
gold-facet position is 1.** SLURP's dead-direct gold facet is typically already the top-ranked
facet in the whole KB; it is not sitting just under a threshold waiting for a better key. The
dead-direct-versus-label-recovered below-τ gap on SLURP is **+2.72 pp** and **+4.54 pp**, against
A2T's **+58.88 pp**.

**Would an informative query plausibly clear it on SLURP?** *This document does not answer that,
and says so.* The question is a counterfactual about a query that was never embedded, and
measuring it requires an embedding contact this row may not take. What can be said from the
observed distribution alone is narrower and is all that is claimed: **on SLURP's dead-direct set
the τ gate is not the dominant obstacle in the first place** — 93.75 % and 91.57 % of those gold
facets already clear it — so the headroom a better key could recover through the τ stage on SLURP
is bounded above by 10 and 14 trajectories per 500. Whether any of them would in fact clear it is
unmeasured. On A2T the corresponding bound is 9 of 15, but the A2T diagnosis §3.2 already measured
that **0 of 11** gold values enter the supply at any depth under the locked `top_l` — so on that
carrier clearing τ is necessary and provably not sufficient.

---

## 6. The two-sided falsifier for the candidate fix

**Candidate: SQ — "contact-0 emits a retrieval query SEPARATELY from its answer attempt, so the
query stays informative when the answer is empty."**

### 6.1 Which trap category this tests, and why

**SQ is in the SEPARATES category, not the IMPROVE-THE-ANSWER category — and that distinction is
the whole point of the D1 clause below.**

K3 (field-role-constrained contact-0) improves the query **by making the ANSWER better**. On
Audio2Tool that was measured to project dispatch **15/104 → 3/104, −80.0 % relative** (upper-bound
arm) and −13.3 % (lower-bound arm), **worse than the already-rejected E-C variant** (−7 % to
−25 %), because a better-formed contact-0 recovers a direct label and the α veto then suppresses
dispatch. The α veto's structural identity `retain == direct-label-recovered` guarantees this: any
change that increases label recovery decreases dispatch one-for-one. **Every fix in K3's category
inherits that trap.**

SQ does not touch the answer field. `default_label_normalizer` / `a2t_label_normalizer` sees the
same string it saw before, so the retain/dispatch decision is expected to be **invariant** by
construction. **That expectation is a design argument, not a measurement**, which is exactly why
D1 is stated as a hard bound rather than as a prediction. The named residual risk: asking the core
for a second field changes the decode and can perturb the answer field as a side effect. D1 and D3
are the clauses that catch that, and they must be measured on the same flight rather than argued
away.

### 6.2 The gate, fixed here before any SQ gate runs

> **SQ GATE — MUST IMPROVE (all four, jointly; failing any one refuses the item):**
>
> **I1.** Gold-facet **recall@1** on the *dead-direct* subgroup rises by **≥ +5.0 pp** under the
> separated query, measured on the carrier whose dead-direct subgroup has the power to see an
> effect that size. *Recall@1, not recall@5: this is the K1 correction, stated first because K1's
> own falsifier omitted it — recall@5 rose while recall@1 fell 23/500.*
>
> **I2.** Median **gold-facet cosine** on the dead-direct subgroup rises by **≥ +0.03** toward the
> label-recovered subgroup's value **on the same flight**.
>
> **I3. DEGENERACY CLAUSE, carried from the A2T gold-absence diagnosis and RE-ANCHORED here.**
> **On Audio2Tool** it applies exactly as the diagnosis wrote it: distinct query vectors per
> dead-direct trajectory rises to **≥ 0.90**, against a measured 0.333 dead-direct and 0.944
> label-recovered on that carrier. A separated query that emits the same skeleton on every empty
> answer changes the text and not the key, and would pass I1/I2 by accident on a small sample while
> fixing nothing. **It does NOT apply verbatim on SLURP**: this row measures SLURP's dead-direct
> subgroup at **0.850** (unexposed NEW500) and **0.735** (exposed DEV-500) against a
> **label-recovered reference of 0.685 and 0.716** on the same halves. SLURP's dead-direct keys are
> already *more* diverse than that carrier's own healthy reference, so an absolute 0.90 bar would
> demand of the dead-direct subgroup something the label-recovered subgroup does not meet either.
> On SLURP the clause binds as **D5**.
>
> **I4.** At SUPPLY level, after the τ / top-`m` / `top_l` stages: **newly gold-supplied among
> currently-WRONG dispatched > gold-supply LOST among currently-CORRECT**. Rank-level improvement
> does not substitute; this is the account K1 failed (12 gained against 29–40 lost).
>
> **SQ GATE — MUST NOT DEGRADE (breaching any one refuses the item):**
>
> **D1. DISPATCH-PRESERVATION CLAUSE, mandatory.** Projected **dispatch count falls by no more than
> 10 % relative** on the gated population, measured from the flight's own landed answers through
> the SAME label normalizer. This is the clause that refused K3 on Audio2Tool (−13.3 % on the most
> conservative arm, **−80.0 %** on the arm that measures actual form repair). SQ *expects*
> invariance here. If the measurement says otherwise, **SQ is an off-switch in disguise and is
> refused exactly as K3 and E-C were** — the design argument does not get to override the number.
>
> **D2.** Gold-facet **recall@1 on the label-recovered (retained) subgroup does not fall.** SQ
> rewrites the query on EVERY trajectory, not only the dead-direct ones, and on A2T 60 of the 89
> retained are already correct.
>
> **D3.** **No currently-CORRECT retained trajectory moves into dispatch.** The α veto's structural
> guarantee (`retain == direct-label-recovered`) is what keeps evidence away from correct answers;
> a change that breaks a label recovery converts a correct retain into a dispatch, which the
> measured anchors price at a loss.
>
> **D4.** The conversion-weighted product **reach share × within-reach conversion**, projected with
> the measured rank anchors (98.2 % at fused top-1, 69.6 % at rank 2–3, 0 % absent — cited to
> `analysis.k1_hybrid_ranking_gate.ANCHOR_TOP1 / ANCHOR_RANK23 / ANCHOR_ABSENT`), **does not fall.**
>
> **D5. DEGENERACY NON-DEGRADATION — the SLURP-binding form of I3.** Distinct query vectors per
> trajectory **does not FALL** on either subgroup of either carrier, measured against that
> carrier's OWN landed values (A2T 0.333 / 0.944; SLURP unexposed 0.850 / 0.685; SLURP exposed
> 0.735 / 0.716), **and the dead-direct subgroup does not fall below its own carrier's
> label-recovered reference.** On SLURP this is the operative clause: the keys there repeat because
> short labels COLLIDE, not because answers are empty (structurally empty dead-direct answers are
> 2/160 and 3/166), so **the only way a separated query can hurt SLURP is by collapsing its keys
> toward a shared query skeleton — which is exactly the failure mode a role-schema-shaped separated
> query is most likely to produce.**
>
> **Reporting rule.** A negative outcome is the finding and is reported as such. The query
> construction, the separated-field schema and the prompt text are fixed in the gating module
> before it runs, and none may be re-tried after the answer is seen. Any SQ flight is NEW400-tier
> or larger, read once, per the key-construction plan §6's statistical-honesty clause.

**Authority: PRE-REGISTERED ONLY.** This falsifier opens no gate, authorizes no flight, and is not
an agenda item. SQ needs its own registration and its own owner decision.

---

## 7. Corrections carried

Per repository discipline, a claim in an existing document that this row's computation contradicts
or bounds is corrected explicitly rather than quietly. None of these changes a headline number in
any landed artifact, and **no immutable record is rewritten in place** — this section is the
English successor.

**C1 — `docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md` §7.2, clause I3, and the identical
text in that row's receipt (`k3_dispatch_projection`). MIS-ANCHORED WHEN READ ON SLURP.** The
sentence is:

> "**I3.** **Distinct query vectors per dead-direct trajectory** rises to **≥ 0.90** — the
> label-recovered subgroup's measured value on this carrier is 0.944 and the dead-direct
> subgroup's is 0.333 (§4.1)."

Read together with that gate's I1, which directs measurement to "the SLURP DEV-1000 unexposed-500
dead-direct subgroup (n = 160)", the 0.90 bar becomes a SLURP-measured bar while remaining
A2T-calibrated. **On SLURP this row measures the dead-direct subgroup at 0.850 (unexposed) and
0.735 (exposed) against a LABEL-RECOVERED reference of 0.685 and 0.716.** Applied verbatim, I3
would demand of SLURP's dead-direct subgroup a key diversity that SLURP's own healthy subgroup does
not reach — an unsatisfiable-by-construction clause that would refuse a working change. The bar is
correct **on Audio2Tool**, where the label-recovered reference really is 0.944. **On SLURP the
clause must bind as a non-degradation bound against that carrier's own label-recovered reference**,
which is §6.2's D5. The diagnosis's I1 figure of n = 160 is **confirmed exactly** by this row. The
diagnosis is not rewritten; whoever next opens the K3 gate must carry this correction with it.

**C2 — `docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md` §4.1, BOUNDED rather than
contradicted.** The sentence is:

> "**Ceiling B is not merely correlated with ceiling A on Audio2Tool — it is largely CAUSED by
> it.**"

That statement is **scoped to Audio2Tool and is confirmed** — this row reproduces every number
under it. What this row adds is the boundary the diagnosis could not draw, because it opened no
SLURP run directory (its own §9.1): **the causal chain does not transfer.** On SLURP the α veto's
dead/live degeneracy ratio is **1.240 and 1.027**, i.e. **≥ 1 on both halves** — the veto selects
the *more* key-diverse subset, so on that carrier ceiling B cannot be caused by ceiling A through
this mechanism. The diagnosis's §9.5 caution ("the degeneracy is a mechanical property of 'the
empty answer is the query' and is very unlikely to be population-specific") stands as written: it
IS a mechanical property, and it is *carrier*-specific rather than population-specific, because the
trigger — an empty answer — occurs at 93.3 % on A2T and 1.25–1.81 % on SLURP.

**C3 — `docs/readiness/2026-08-25-key-construction-agenda-plan.md` §2.2, the causal clause BOUNDED;
the deficit itself REPRODUCED on a new population.** The sentence is:

> "33–37% of samples produce a first answer naming no TRAIN intent. Their retrieval is measurably
> worse (gold-in-top-5 66.2–67.6% vs 71.6–74.1% for label-recovered samples; gold-facet cosine
> 0.775 vs 0.828) **because the query vector IS the direct answer's embedding**."

The **deficit is reproduced** on DEV-1000, a population that band did not cover: dead-direct rate
**32.0 %** (unexposed) and **33.2 %** (exposed) — the unexposed half sits just below the quoted
33–37 % floor; gold-in-top-5 **70.00 % vs 76.47 %** and **69.88 % vs 75.45 %**; median gold-facet
cosine **0.800 vs 0.835** and **0.772 vs 0.840**. The clause this row **bounds is the "because"**.
The premise is true — the query vector IS the direct answer's embedding, proved here on 1000 of
1000 samples — but it does not entail the conclusion on this carrier, because SLURP's dead-direct
queries are **more** distinct than its label-recovered ones (0.850 vs 0.685; 0.735 vs 0.716). **Key
collapse is refuted as the cause of SLURP's dead-direct deficit.** The deficit is real; its cause
is not identified here (§4.4). This section is that plan's English successor for its §2.2 causal
clause; the plan itself is NOT rewritten, and whoever next opens it should append this outcome in
the same additive form its §6 used for the K1 gate outcome.

**C4 — no contradiction found elsewhere.** The A2T diagnosis's §4 dead-direct contrast (26.67 % vs
71.91 %; 0.6054 vs 0.8632), its §4.1 degeneracy block (5/15, 11-cluster, 84/89, one supply) and its
§3.2 τ band (0.5653–0.6356 on nine trajectories) are each reproduced **exactly** here on an
independent code path. The cross-carrier transfer verdict's compounding statement is scoped to
Audio2Tool in its own text and is untouched.

**C5 — a correction this row cannot carry, named with its owner.** The prior-dimension defect in
`rails/knowledge_build_a2t.py` (`prior_score = tool_total / category_total` is not a conditional
probability) is recorded in `kb_policy._dimension_scales`'s docstring and bounded to zero effect by
the A2T diagnosis §3.4. It is untouched here and remains open; it belongs to whoever owns
`rails/knowledge_build_a2t.py`, and this row changed no code under `rails/`.

---

## 8. Not verified, and therefore not used

Listed so their absence is visible rather than inferred.

1. **A positive account of SLURP's residual dead-direct deficit.** This row refutes key collapse as
   its cause and identifies no replacement. The leading candidate — a wrong-but-informative key
   pointing at the wrong neighbourhood — is untested, and the standing confound (bad key vs
   intrinsically harder sample) is unresolved and cannot be resolved offline.
2. **Any counterfactual about a differently-constructed query.** §5 reports observed τ distances
   only. Measuring where a gold facet would sit under a separated query needs an embedding contact
   this row may not take, and no clearing projection is made on either carrier.
3. **The K3 or SQ dispatch projection for SLURP.** The A2T diagnosis §9.1 left this open and this
   row does not close it: no dispatch projection of any kind was computed on the SLURP side here.
   D1 in §6.2 states the bound; it does not measure it.
4. **Whether the degeneracy reproduces on an unexposed A2T population.** Carried forward unchanged
   from the A2T diagnosis §9.5. The 104 are exposed and below the campaign's n ≥ 400 power floor.
5. **Any variance estimate on the statistics in §3.** No bootstrap, no interval, no significance
   test was computed for any degeneracy or content statistic here; they are descriptive counts over
   sealed records, and the dead-direct groups on SLURP (160, 166) are large while the A2T
   dead-direct group (15) is a mechanism reading and never an effect size.
6. **Why the SLURP embedding is not bit-stable on identical texts** (§3.3 caveat 2). Measured, not
   explained. It is consistent with batch-composition float variation in the embedding sidecar; no
   contact was taken to confirm that, and no conclusion here depends on it.

---

## 9. HARD STOP — what this document does NOT authorize

This is a **measurement over landed evidence at zero contacts**. It authorizes:

- **nothing to fly.** No model contact, no tool contact, no embedding contact, no flight, no
  re-flight, no G2 opening, no new attempt on any run id. The resident service was not touched.
- **no knob change.** τ, `m`, `c`, `top_l`, `top_k`, α and the rank weights are read and reported,
  never written. `configs/`, `rails/` and `core/` are untouched. §5's finding that 10 and 14 SLURP
  dead-direct gold facets sit below τ is a **measurement, not a proposal**, and nothing here
  licenses moving τ.
- **no revision of the lock.** The SLURP unexposed NEW500 statistics are a **SECONDARY READING**.
  They do not revise, re-tune, restate or re-open `SAEA-DEV1000-BASELINE-LOCK`, whose read was
  one-shot and is closed. The locked cell's headline (+20.20 pp, CI [+17.2, +23.4]) is untouched
  and is not restated as a finding of this row.
- **no SQ item, no SQ gate and no SQ flight.** §6 pre-registers a two-sided falsifier so that a
  future gate cannot be parameterised after seeing its own numbers. It does not open that gate, on
  either carrier, and SQ is not an agenda item until it has its own registration and an owner
  decision.
- **no K3 decision for SLURP.** K3 stays REFUSED for Audio2Tool on D1 (the A2T diagnosis §7).
  Its status on SLURP is untouched, unprojected and explicitly not established here.
- **no `rails/` repair.** §7 C5 names the open prior-dimension defect and its owner; fixing it is a
  separate authorized change and is not this row's.
- **no generality claim and no superiority claim.** No result about SLURP or Audio2Tool as tasks
  follows from this artifact. The A2T-G1-104 population is exposed with a 0.0 pp exact-match delta;
  the SLURP halves are dev-tier.
- **no test contact. FINAL60 stays reserved.** No Stage-3 activity: Stage-3 requires
  `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT` into a `papers/<slug>` repository and this repository
  never accepts it.

`consumed` stays **no**: no seal is broken by this row. Gold was opened scoring-side only, over
populations whose seals the landed DEV-1000 lock read and the landed A2T G1 read had already
broken, and never on a runtime path.
