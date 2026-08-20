# P-EMB-3L verdict — LOCAL-EXHAUSTED (registered one-shot read, 2026-08-20)

Mechanical outcome per the registered metrics and verdict rules
(`docs/readiness/2026-08-20-pemb3l-preregistration-REGISTERED.md` §3, as scoped by the pre-read
instrument amendment §6), computed by the pinned offline read suite (`analysis.pemb3l_read`, built
and coordinator-reviewed BEFORE the read, flown unmodified) over the already-flown sweep
`SAEA-PROBE-pemb3l-234` — 234/234 embedding contacts across two attempts on one plan
(`attempt-20260820T062543Z-e91099` L1+L2, `attempt-20260820T065009Z-1361ad` L3, `error: null`,
durable state `FINALIZED`) — zero model contact, zero GPU, no attempt-directory mutation.

Read archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb3l-read/`
(`verdict.json`, `report.txt`, `README.md`, `MANIFEST.sha256`). The suite ran exactly once
(idempotence-guarded output dir), exit 0, at study HEAD `063c056` with a clean tree. Exposure row
`SAEA-PROBE-pemb3l-234` flips to consumed in the same commit. Scope: **descriptive, discovery-tier,
n = 60 SLURP devel, 18 canonical labels, three arms, single run per arm, same-distribution**. SLURP
audio CC BY-NC 4.0 carried on every number below.

Pre-read gates, all green before anything was opened: `test_pemb3l_read.py` **24 passed**; the
flight archive's `MANIFEST.sha256` verified **47/47 OK**; ledger row `consumed = no`; tree clean at
`063c056`. `PYTHONDONTWRITEBYTECODE=1` throughout. The read consumed only the three derived per-arm
vector manifests (`derived/embeddings/SAEA-PROBE-pemb3l-234/<arm>/manifest.json`, 78 entries each,
all dim 2048, 78 distinct vector sha256 per arm) plus scoring-side-only gold.

---

## 1. VERDICT

> ## OVERALL: **LOCAL-EXHAUSTED**
> every training-free embedding construction this build can express fails identically; the local
> core's representation is exhausted, and the external dedicated-embedder path becomes the routing
> tier's representation instrument

| arm | pooling | prefix (both sides) | accuracy | labels ever predicted | top-1 share | top-2 share |
|---|---|---|---|---|---|---|
| **L1 last-bare** | `last` | none | **3 / 60 = 0.0500** | **5 / 18** | 0.4833 (`general` 29) | 0.9167 |
| **L2 last-instruct** | `last` | GritLM-style | **3 / 60 = 0.0500** | **2 / 18** | 0.9333 (`qa` 56) | 1.0000 |
| **L3 mean-instruct** | `mean` | GritLM-style | **3 / 60 = 0.0500** | **2 / 18** | 0.6333 (`datetime` 38) | 1.0000 |
| *mean-bare (CITED, consumed P-EMB-1)* | `mean` | none | *0.0500* | *5 / 18* | *0.4833* | *0.9167* |

**All three arms return exactly 3/60.** The decision weight rides on L1/L2 (the last-pool arms, per
the owner's no-pooling directive); both read 0.0500, identical to the arm the probe was launched to
beat.

### Against the registered thresholds

| clause | result | margin |
|---|---|---|
| **LOCAL-SPACE-EXISTS**: any arm ≥ 0.30 | **not met** | best arm 0.0500 vs floor 0.30 — short by **0.2500**, i.e. **15 samples**; an arm would have needed 18/60 and returned 3/60 |
| **LOCAL-EXHAUSTED**: every arm ≤ 0.15 | **MET, on all three** | 0.0500 vs ceiling 0.15 — clears by **0.1000** (6 samples); the best arm sits **three-fold** inside the ceiling |
| **INCONCLUSIVE-EMB3L** (otherwise) | not reached | — |

### Against the comparators (same frozen 60 SLURP devel samples, same frozen core)

| comparator | scenario accuracy |
|---|---|
| A1′r / P-FEW FS-NONE closed-set decode routing (cited, consumed) | **0.7833 – 0.8167** |
| best constant predictor (always `calendar`, the modal gold class) | 0.1333 |
| uniform chance over 18 labels | **0.0556** |
| **every P-EMB-3L arm** | **0.0500** |

**All three arms are below uniform chance, below the best constant predictor, and roughly
sixteen-fold below the decode router measured on the identical samples.** The registered branches
were both live before the data was opened; this one fires by a wide margin and is not a threshold
artifact.

---

## 2. The result is fully explained by each arm's own prediction marginal

Descriptive, unregistered, no clause attaches. For each arm, re-pair the exact same 60 predicted
labels to the exact same 60 samples at random; the analytic expectation of hits is:

| arm | observed hits | expectation under random re-pairing of its OWN predictions | observed − expected |
|---|---|---|---|
| L1 last-bare | 3 | **4.300** | **−1.300** |
| L2 last-instruct | 3 | **4.867** | **−1.867** |
| L3 mean-instruct | 3 | **3.733** | **−0.733** |

**Every arm scores below the expectation of its own shuffled prediction vector** (uniform chance
expects 3.333 hits of 60). There is no detectable audio-content signal in any argmax. The three
hits per arm are coincidences of attractor absorption:

- **L1** — `slurp:devel:004134…-headset → play` (cos +0.0808), `slurp:devel:005684 → play`
  (+0.0236), `slurp:devel:006603 → general` (+0.0082). All inside the two attractors.
- **L2** — all three hits are `qa`, the label the arm emits **56 times out of 60**, and all three
  carry **negative** cosines (−0.0188, −0.0214, −0.0294). The arm hit 3 of the 5 `qa` golds by
  predicting `qa` almost everywhere.
- **L3** — `datetime` ×2 (−0.1398, −0.1844) and `qa` ×1 (−0.2534); `datetime` is emitted 38 times.

Correct-set overlap across arms is essentially nil: L1∩L2 = ∅, L1∩L3 = ∅, L2∩L3 = one sample
(`slurp:devel:014173`). Per-sample predicted-label agreement is **0/60** (L1 vs L2), **1/60**
(L1 vs L3) and **26/60** (L2 vs L3). The arms do not agree on *which* samples they get right,
because none of them is deciding on content.

---

## 3. Confusion and attractor structure — the instruction prefix made the collapse WORSE

| arm | prediction distribution | never predicted |
|---|---|---|
| L1 last-bare | `general` 29, `play` 26, `transport` 3, `datetime` 1, `iot` 1 | 13 of 18 labels |
| L2 last-instruct | **`qa` 56, `datetime` 4** | **16 of 18 labels** |
| L3 mean-instruct | **`datetime` 38, `qa` 22** | **16 of 18 labels** |

**The GritLM-style instruct prefix — the probe's principal new lever — collapses the argmax from
five attractors onto two.** Both instructed arms place their entire mass on two labels; L2 puts
93.3 % of it on a single label. `calendar`, the modal gold class with 8 of the 60 samples, is never
predicted by any arm. Representative confusion cells: `calendar → play` 6 and `qa → general` 4
(L1); `calendar → qa` 8, `play → qa` 7 (L2); `calendar → qa` 6, `play → datetime` 4 (L3) — gold
classes of every kind funnelling into a handful of attractors with no visible relation between the
gold class and which attractor absorbs it.

This is the **direct confirmation of E-0's dilution finding** that the P-EMB-1 verdict §3 named as
confound 3: *a prompt prefix shifts the pooled vector more than swapping the audio does*. Adding a
prefix to both sides in common mode was the registered attempt to exploit that geometry; it instead
demonstrated it, by moving the pooled representation so far toward the format-determined centroid
that the candidate field narrowed from five reachable labels to two.

### Cosine geometry

| statistic over each arm's 60 winning (audio, label) pairs | L1 | L2 | L3 |
|---|---|---|---|
| max | +0.0808 | +0.0908 | +0.0127 |
| mean | **+0.0377** | **+0.0042** | **−0.1846** |
| median | +0.0366 | +0.0040 | −0.1853 |
| min | −0.0012 | −0.0732 | −0.3073 |
| pairs with a positive cosine | 59 / 60 | 33 / 60 | **1 / 60** |
| top-1 cosine range (max − min) | 0.0820 | 0.1640 | 0.3200 |

Vectors are L2-normalized on both sides, so the top-1 cosine is directly interpretable. **The
nearest label is essentially orthogonal to the audio in the two last-pooled arms** (means +0.038
and +0.004), and **anti-aligned in the mean-pooled instructed arm** (mean −0.185, only one of 60
samples having any positively-similar label at all). L3 reproduces on SLURP the uniform
anti-alignment that P-EMB-2 measured on Audio2Tool. Widening the cosine spread (0.082 → 0.164 →
0.320) buys no accuracy: the spread is attractor geometry, not discrimination.

---

## 4. §6.2(c) structural check — CONFIRMED, and stronger than predicted

The amendment predicted L1's audio side to be byte-identical to the consumed P-EMB-1 audio side
(both bare; they differ only in the pooling flag). Checked against the CONSUMED P-EMB-1 vector
manifest — exposure row `SAEA-PROBE-pemb1-78`, `consumed = yes` (2026-08-19), artifacts therefore
readable — at `derived/embeddings/SAEA-PROBE-pemb1-78/manifest.json`:

> ### **L1 audio vs P-EMB-1 audio: 60 / 60 byte-identical.** Prediction confirmed.

60 shared contact ids, 60 distinct sha256 on each side, zero mismatches. **The `--pooling` flag has
no effect whatsoever on the audio side of this build.** The consequences the amendment attached to
this result therefore hold:

1. **The "mean vs last" audio contrast does not exist on this build at all.** P-EMB-1's own verdict
   §3 named "last-token or attention-weighted pooling instead of mean" as one of three ways a
   successor might rescue embedding routing. P-EMB-3L flew that successor, and the structural check
   shows the audio side never changed. That rescue route was **not tested and cannot be tested
   through this build's `--pooling` flag**.
2. **Audio-side construction variation in this sweep spans only the instruction-prefix axis.**

### The check ran further, and L1 turns out to be a near-total replay of P-EMB-1

| comparison | result |
|---|---|
| L1 audio vs P-EMB-1 audio | **60 / 60** byte-identical |
| L1 text vs P-EMB-1 text | **15 / 18** byte-identical |
| labels whose text vector the `last`/`mean` flag actually changed | exactly **3**: `cooking`, `recommendation`, `takeaway` |
| L1 vs P-EMB-1 per-sample predicted label | **60 / 60 identical** |
| L1 vs P-EMB-1 top-1 cosine floats | **60 / 60 bit-identical** |

The three text vectors the pooling flag moved are the only multi-token labels in the roster, and
**none of them was ever the argmax winner in either run** — so the change was invisible to every
number. **L1 is a bit-exact reproduction of the consumed P-EMB-1 result**, not merely an equal one:
same 3 correct ids, same `general` 29 / `play` 26 distribution, same 5-of-18 reachable labels, same
cosines to the last float.

### Distinct constructions the 234 contacts actually realized

| side | distinct vector sets across P-EMB-1 + the three arms |
|---|---|
| **audio** | **2** — {P-EMB-1, L1} (bare) and {L2, L3} (instructed) |
| **text** | **4** — all four distinct |

**Of the 234 contacts, the 78 spent on L1 re-derived an already-consumed result to the bit**, and
the sweep explored exactly **one new audio-side construction** (the instructed prefix) rather than
the three the arm table implies. This is an accounting fact about what the flight could express, not
a defect in the flight, which flew the registered machinery unmodified.

---

## 5. Interpretation scope, as fixed by §6 before the read

Per §6.2, and stated here so no number above is over-read:

- **L2-vs-L3 is a TEXT-side-only pooling contrast on this build.** The two arms share all 60 audio
  vectors byte-for-byte (fly-archive `cross-arm-identity.log`, re-confirmed by this read's own
  grouping). Their accuracy tie at 0.0500 and their differing attractors (`qa`-dominant vs
  `datetime`-dominant) are properties of the text side alone.
- **L3-vs-cited-mean-bare inherits the same text-side-only scope** per §6.2(b). The registered
  common-mode delta is **+0.0000** (0.0500 − 0.0500). *Flagged for the coordinator:* structurally,
  this pair is **not** audio-invariant — L3's audio vectors share **0/60** with P-EMB-1's, because
  what varies between them is the *prefix* (which demonstrably moves both sides), not the pooling
  flag (which moves only text). A reading of the +0.0000 as a **both-sides common-mode prefix null**
  is the one the byte evidence supports, and it is the stronger statement; §6.2(b)'s narrower scope
  is preserved above as registered. Both readings yield the same number and the same verdict.
- **§3's verdict criteria are unchanged** and were computed exactly as registered.
- **LOCAL-EXHAUSTED is scoped, per §6.3, to the constructions this build can actually express**:
  audio ∈ {effective-pool bare, effective-pool instructed} × text ∈ {last, mean} × {bare,
  instructed}. It is **not** a claim about last-token audio pooling, which this build cannot
  deliver, nor about attention-weighted pooling, learned projections, or the audio-span-only pooling
  patch E-0 described — none of which was reachable here.

---

## 6. What this decides for P-EMB-3M

The verdict is **LOCAL-EXHAUSTED**, so §3's registered consequence fires:

> **The dedicated-embedder path P-EMB-3M becomes the routing tier's representation instrument.**

The local-first directive of 2026-08-20 is discharged, negatively. The local omni core was tried
first, across every training-free construction the pinned build can express, and returned 0.0500 on
all of them — the same number, and in L1's case the same bits, as the construction P-EMB-1 already
refuted. No further local construction may be flown as a re-cut of these vectors; they are spent and
the row is consumed.

**Three carry-forwards P-EMB-3M must absorb, all established by this read:**

1. **The pooling-override defect is a build property and must be checked before it is trusted.**
   On this llama.cpp build, audio-containing embedding requests have their pooling overridden — the
   server logs `embeddings required but some input tokens were not marked as outputs -> overriding`
   exactly once per audio contact and never for text, and the byte evidence confirms the flag is
   inert on audio. **E-1's primary P-EMB-3M arm, LCO-Embedding-Omni-3B GGUF, is documented as a
   last-token-pooling model and is planned on this same pinned build.** If the override applies
   there too, LCO would be run in a pooling mode its contrastive training never used, and a null
   result would be uninterpretable. P-EMB-3M must therefore carry a **pre-flight structural check:
   embed the same audio twice under `--pooling last` and `--pooling mean` and confirm the vectors
   DIFFER**, before any scored contact is spent. This read supplies the exact instrument
   (`cross_arm_identity`-style sha256 comparison) and the exact failure signature to look for.
2. **The instruction-prefix axis is refuted on the local core and unproven elsewhere.** The prefix
   did not merely fail to help; it narrowed the reachable label set from 5 to 2. A dedicated
   embedder trained with instruction prefixes (GritLM-style, as LCO is) may behave oppositely, but
   the prefix must be an *arm*, not an assumption.
3. **The comparator bar is unchanged and high.** Any dedicated embedder must beat 0.0556 (chance),
   0.1333 (best constant predictor) and, to matter at all, approach 0.7833–0.8167 (closed-set decode
   routing on these identical 60 samples). LOCAL-SPACE-EXISTS' 0.30 floor remains the natural
   registration floor for the successor.

Nothing here authorizes P-EMB-3M. It is a design input; the probe needs its own registration,
owner-scoped ceilings, and pre-registered exposure row, and the charter's pinned-and-logged
tool-level retriever clause governs any external model it adopts.

---

## 7. Bounds carried by every statement above

n = 60 SLURP devel, 18 canonical labels, three arms, one run per arm, one carrier, one frozen core,
one quantization (q4km), discovery tier. Two of the three arms share an audio side; one arm is a
bit-exact replay of a previously consumed probe. The marginal-expectation figures in §2 are
**descriptive, unregistered, analytic** and carry no clause; no permutation simulation was run. The
cited mean-bare 0.0500 is **cited** from the consumed P-EMB-1, not co-measured. Byte-identity
checks compare sha256 of stored vectors only — **no vector values were compared** and no similarity
was computed across probes. Gold scenarios were used scoring-side only and never entered a runtime
path. SLURP audio CC BY-NC 4.0 carried. No test split was touched. No superiority, generalization,
deployment, or paper-scale claim attaches to any number in this document.
