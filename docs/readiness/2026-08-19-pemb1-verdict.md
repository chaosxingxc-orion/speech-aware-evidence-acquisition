# P-EMB-1 verdict — EMB-WEAK (registered one-shot read, 2026-08-19)

Mechanical outcome per the registered metrics and verdict rules
(`docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md` §2, Run A), computed by the pinned
offline read suite (`analysis.pemb_read run-a`, coordinator-reviewed before the read) over the
already-flown attempt `attempt-20260819T235907Z-49567c` (`SAEA-PROBE-pemb1-78`, status `COMPLETED`,
error `None`, durable state `FINALIZED`, 78/78 embedding contacts = 60 audio + 18 text) — zero
model contact, zero GPU, no attempt-directory mutation.

Read archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-19-pemb1-read/`
(`verdict.json`, `report.txt`, `README.md`, `MANIFEST.sha256`). The suite ran exactly once
(idempotence-guarded output dir), exit 0, at study HEAD `162cca3` with a clean tree. Exposure row
`SAEA-PROBE-pemb1-78` flips to consumed in the same commit. Scope: **descriptive, discovery-tier,
n = 60 SLURP devel, 18 canonical labels, single run, same-distribution**. SLURP audio CC BY-NC 4.0
carried on every number below.

Pre-read gates, all green before anything was opened: `test_pemb_read.py` **41 passed**; the flight
archive's `MANIFEST.sha256` verified **30/30 OK**; ledger row `consumed = no`; tree clean at
`162cca3`. `PYTHONDONTWRITEBYTECODE=1` throughout. The read consumed only the derived vector
manifest (`derived/embeddings/SAEA-PROBE-pemb1-78/manifest.json`, 78 entries, all dim 2048, 78
distinct vector sha256) and never touched the attempt directory — every attempt-dir and derived-root
file mtime is 20:02 and predates the 20:53 read, post-read attempt fingerprint `74494701…2839`.

---

## 1. VERDICT

> ## OVERALL: **EMB-WEAK**
> bare cross-modal matching does not form a usable shared space on this core; the routing tier
> stays decode-based

| quantity | value |
|---|---|
| samples | **60** |
| candidate labels | **18** canonical SLURP scenarios |
| **argmax-cosine accuracy vs gold** | **3 / 60 = 0.0500** |

### Against the registered thresholds and the cited comparators

| clause | result | margin |
|---|---|---|
| **EMB-ROUTES**: accuracy ≥ 0.65 | **not met** | 0.0500 vs floor 0.65 — short by **0.6000** (36 samples) |
| **EMB-WEAK**: accuracy ≤ 0.30 | **MET** | 0.0500 vs ceiling 0.30 — clears by **0.2500** (15 samples) |
| **INCONCLUSIVE-EMB1** (otherwise) | not reached | — |

| comparator (all on the same frozen 60 SLURP devel samples, same frozen core) | scenario accuracy |
|---|---|
| **A1′r closed-set decode routing** (cited, consumed 2026-08-18) | **0.7833** (47/60) |
| **P-FEW FS-NONE closed-set decode routing** (in-session, consumed 2026-08-19) | **0.8167** (49/60) |
| **A0 free-form decode** (cited, ≈ 6/360 exact scenario hits) | **≈ 0.10** |
| uniform chance over 18 labels | 0.0556 |
| best constant predictor (always `calendar`, the modal gold class) | 0.1333 |
| **P-EMB-1 argmax cosine** | **0.0500** |

**The embedding router does not merely lose to the decode router — it loses to guessing.** At
0.0500 it sits below uniform chance over its own label set (0.0556), below the best single-label
constant predictor (0.1333), below the free-form decode floor the registration cited as the weak
comparator (≈ 0.10), and roughly **sixteen-fold** below the closed-set decode router measured on
the identical samples this same week. Both registered branches were live before the data was
opened; this one fires by a very wide margin and is not a threshold artifact.

---

## 2. Confusion structure — a collapse, not a routing error

The failure is not diffuse misrouting. **The argmax collapses onto two attractor labels.**

| predicted label | count | share of 60 |
|---|---|---|
| **`general`** | **29** | 48.3 % |
| **`play`** | **26** | 43.3 % |
| `transport` | 3 | 5.0 % |
| `datetime` | 1 | 1.7 % |
| `iot` | 1 | 1.7 % |
| *(the other 13 canonical labels)* | **0** | **0.0 %** |

**Five of eighteen labels were ever predicted; two of them absorb 55 of 60 samples (91.7 %).**
Thirteen canonical scenarios — including `calendar`, the modal gold class with 8 of the 60 samples —
were never the nearest label for any audio clip in the set. A router with a live decision would
have to place at least *some* mass on the classes that dominate the gold distribution. This one
places none.

The confusion table (full version in `verdict.json` / `report.txt`) is therefore best read
column-wise rather than row-wise: almost every gold class maps into `general` or `play`, and which
of the two it lands in carries no visible relation to content — `calendar → play` (6),
`qa → general` (4), `play → general` (4), `iot → general` (3), `transport → play` (3),
`cooking → play` (2), `music → play` (2), `news → general` (2), `weather → general` (2).

### The three correct predictions are coincidences of the collapse

| sample_id | gold | predicted | top-1 cosine |
|---|---|---|---|
| `slurp:devel:004134:audio-1500387396-headset` | `play` | `play` | 0.0808 |
| `slurp:devel:005684:audio-1498577434` | `play` | `play` | 0.0236 |
| `slurp:devel:006603:audio-1502101512` | `general` | `general` | 0.0082 |

All three sit inside the two attractors. None is a class the router ever reaches by discrimination.
This can be made precise without any new measurement, as a descriptive, unregistered check:

> **Re-pair the exact same 60 predicted labels to the exact same 60 samples at random.** The
> expected number of hits is **4.30** — *more* than the 3 actually observed. A permutation test
> (N = 100,000, seed 20260807, shuffling only the prediction vector) gives
> **P(hits ≥ 3) = 0.8774**, with the shuffled distribution centred at 5.

The observed agreement with gold is thus **entirely accounted for by the prediction marginal alone**,
and in fact falls slightly below its expectation. **There is no detectable audio-content signal in
the argmax.** The accuracy figure of 0.0500 should not be read as "weak routing"; it should be read
as **no routing**, with the small nonzero value being an artifact of two attractor labels happening
to coincide with two gold classes.

### The cosines say the same thing geometrically

Vectors are L2-normalized on both sides (`--embd-normalize` at its default 2, the registration's
"cosine = dot"), so the top-1 cosine is directly interpretable.

| statistic over the 60 winning (audio, label) pairs | value |
|---|---|
| max | **0.0808** |
| mean | **0.0377** |
| median | **0.0366** |
| min | **−0.0012** (one negative winner) |
| below 0.05 | **42 / 60** |

**The nearest label is, in every single case, essentially orthogonal to the audio.** The winning
similarity never exceeds 0.081, and on one sample the *best available* label out of eighteen has a
negative cosine — i.e. no label in the candidate set is even weakly aligned with that clip. There is
no shared audio-text region in this space; the argmax is picking the least-orthogonal of eighteen
near-orthogonal directions, which is a norm/direction artifact of the text side rather than a
content match. That is exactly what the two-attractor collapse looks like from the geometry side,
and the two observations are the same fact seen twice.

---

## 3. What this means, and what it does not

**What the result licenses.** On this frozen core, with the registered construction — the pinned
q4km GGUF in `--embedding --pooling mean` mode, bare audio bytes on one side, bare canonical label
strings on the other, no instruct prefix on either — **mean-pooled hidden states do not constitute a
shared cross-modal space**. Whole-utterance representation matching is not a viable router here, and
`EMB-WEAK`'s own registered wording is the correct conclusion: *the routing tier stays
decode-based*.

**What the result does not license.** This is a negative on **one construction**, not on embedding
routing as a family. Three specific confounds are named and none of them is resolved by this read:

1. **No contrastive objective exists in the core.** Qwen3-Omni is a generative decoder; nothing in
   its training makes mean-pooled audio states and mean-pooled text states co-locate. Models that
   route by embedding (CLAP-style) are trained for exactly that and this one was not. The negative is
   therefore unsurprising in hindsight and is best stated as a *property of the frozen core's
   representation*, not a refutation of the routing-tier hypothesis.
2. **Severe length and form asymmetry.** The text side is a bare one- or two-token label string; the
   audio side is a multi-second clip (mean 3.04 s, encoder-quantized at ~13 tokens per second, so on
   the order of 40 pooled positions). Mean pooling over sequences that differ by an order of
   magnitude in length, across two modalities, is a weak matching construction independent of
   whether a shared space exists.
3. **The pooled vector is known to be dominated by non-content structure.** E-0's own binding
   measurement — *a prompt prefix shifts the pooled vector more than swapping the audio does* — was
   recorded as a reason to strip prefixes. This read supplies the natural continuation of that
   observation: if format moves the pooled representation more than content does, then a
   content-based argmax over that representation should collapse onto whichever candidates sit
   nearest the format-determined centroid. **It did, onto two of them.** E-0's dilution finding and
   P-EMB-1's collapse are one phenomenon.

A successor that wanted to rescue embedding routing on this core would have to change the
construction — label *sentences* or templated descriptions instead of bare strings, last-token or
attention-weighted pooling instead of mean, or a lightweight learned projection — and each of those
is a fresh registration. **None may be attempted as a re-cut of this attempt**: the vectors are
spent, the row is consumed, and re-embedding is a new model contact requiring its own pre-registration.

**Cost note, for the successor's benefit.** The negative was purchased extremely cheaply: 78 contacts,
0.006 GPU-h (3.1 % of the registered ceiling), 7.55 s of wall time. Whatever else is true, the
embedding tier is *cheap to test*, and a redesigned construction would also be cheap. The economics
that motivated the probe ("a viable router at a fraction of the decode cost") remain attractive; only
this particular realization of it is dead.

---

## 4. The routing-tier reading

The scheme scoreboard's routing tier
(`docs/readiness/2026-08-19-scheme-scoreboard.md`, best-scheme statement v1) offered two candidate
mechanisms for high-order semantics: **closed-set decode prompting** (established) and
**whole-utterance representation matching** (under test, this probe). P-EMB-1 closes the second on
the SLURP carrier.

| routing-tier mechanism | status after this read |
|---|---|
| Closed-set decode routing | ✅ established — 0.78–0.82 gold agreement across two sessions, `{exact: 60}` mapping under three prompt constructions |
| Few-shot demonstration supply on the decode router | ❌ no gain (P-FEW, BAL−NONE +0.0000) |
| **Bare mean-pooled embedding matching** | **❌ no routing at all — 0.0500, below chance, two-attractor collapse, permutation P = 0.8774** |

**Consolidated statement.** Two of the three candidate levers for the routing tier are now
eliminated, and both eliminations are clean rather than marginal. The decode path is not merely the
*best* available router on this core — as of this read it is the **only** one that works at all. The
tier's remaining open direction is not a different *representation* but a different *target*: the
P-FEW read localized more than half the decode router's residual error into a single confusable
label neighbourhood (`play` collapsing into `music`/`audio`/`news`), and corrective, targeted supply
aimed at a measured confusion is the one routing-tier idea this arc has not yet tested.

**Effect on P-TARGET.** The design gate for P-TARGET (router confidence as a supply-targeting
signal) was registered as needing the P-EMB reads. Run A removes one candidate source of that
confidence signal: **cosine margin from this embedding space is not a usable confidence signal**,
because the space carries no content discrimination — a margin computed over near-orthogonal,
collapsed directions cannot rank samples by routing difficulty. If P-TARGET is to be registered, its
confidence signal must come from the decode path (label-token logits, closed-set agreement across
resamples or prompt variants), not from this representation. Run B's read is the remaining input to
that gate and is taken up separately.

**Bounds on every sentence above.** n = 60 SLURP devel, 18 labels, one run, one carrier, one core,
one pooling mode (mean), one text rendering (bare canonical label string), no instruct prefix,
discovery tier. The permutation check in §2 is descriptive and unregistered and carries no clause.
Gold scenarios were used scoring-side only and never entered a runtime path. SLURP audio
CC BY-NC 4.0 carried. No test split was touched. No superiority, generalization, deployment, or
paper-scale claim attaches to any number in this document.
