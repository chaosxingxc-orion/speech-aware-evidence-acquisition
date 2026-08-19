# P-TRAP verdict — ACOUSTIC-MEDIATED (registered one-shot read, 2026-08-19)

Mechanical outcome per the registered metrics and verdict rules
(`docs/readiness/2026-08-19-ptrap-preregistration-REGISTERED.md` §3 as **gated by §6**),
computed by the pinned offline read suite (`analysis.ptrap_read`, coordinator-reviewed before
the read) over the already-flown attempt `attempt-20260819T155046Z-98efbd`
(`SAEA-PROBE-ptrap-120`, status `COMPLETED`, error `None`, 120/120 rows across V1/V2) — zero
model contact, zero GPU, no attempt-directory mutation.

Read archive: `docs/checks/speech-aware-evidence-acquisition/2026-08-19-ptrap-read/`
(`verdict.json`, `report.txt`, `README.md`, `MANIFEST.sha256`). The suite ran exactly once
(idempotence-guarded output dir), exit 0, at study HEAD `26ef46e` with a clean tree. Exposure
row `SAEA-PROBE-ptrap-120` flips to consumed in the same commit. Scope: **descriptive,
discovery-tier, n = 60 SLURP devel (32 usable), single run, same-distribution**. SLURP audio
CC BY-NC 4.0 carried on every number below.

Pre-read gates, all green before anything was opened: `test_ptrap_read.py` **31 passed**; the
flight archive's `MANIFEST.sha256` verified **27/27 OK**; ledger row `consumed = no`; tree
clean at `26ef46e`. The attempt directory was not mutated — every file mtime in it
(11:50–11:54) predates the read (12:39), post-read fingerprint `49a2c9a8…a191`.

---

## 1. REACHABILITY STATEMENT (mandatory §6 item; published BEFORE any verdict was evaluated)

The §6 amendment requires that, given this run's own per-sample K distribution and usable-trap
counts, the **maximum attainable capture difference** be published first, and forbids reporting
an unreachable branch as an affirmative outcome.

| quantity | value |
|---|---|
| samples flown | **60** (V1 60 / V2 60) |
| K distribution (V1, and V2 length-matched exactly) | `{0: 28, 1: 18, 2: 11, 3: 3}` |
| **usable = common denominator (V1 K ≥ 1)** | **32** |
| excluded (K = 0) | **28** |
| best case (V1 captures all usable, V2 captures none) | **max attainable rate diff = 1.0000, max attainable raw diff = 32** |
| ACOUSTIC-MEDIATED floor | rate diff ≥ +0.10 **and** raw diff ≥ 6 |
| **verdict** | **REACHABLE** — rate headroom **+0.9000**, raw headroom **+26** |

**The affirmative branch was reachable with very large margin**, so nothing in this read is
under §6's suppression clause. The equivalence branch (KEY-ONLY-MATCHING) was likewise legally
available: with 32 paired samples the CI can in principle sit wholly inside ±0.03. Both
branches were live before the data was opened.

The one thing the reachability arithmetic hides, and which §2 of this document takes up
directly, is *which* 32 samples survived: the denominator is 32 not because the flight was
small but because a legality check removed most of the trap supply.

---

## 2. VERDICT

> ## OVERALL: **ACOUSTIC-MEDIATED**
> (the §6 CI-gated evaluator, authoritative; the registered §3 point thresholds are met as well)

| quantity | value |
|---|---|
| **capture(V1)** — self-percept traps | **29 / 32 = 0.9062** |
| **capture(V2)** — cross-percept control | **0 / 32 = 0.0000** |
| **rate difference V1 − V2** | **+0.9062** (0.90625) |
| **raw difference** | **+29** |
| **σ̂** paired cluster bootstrap over the per-sample V1−V2 difference | **0.0519** (0.051882) |
| **90 % CI** (N = 10,000 replicates, seed 20260807) | **[+0.8125, +0.9688]** |

### Clause margins (every clause, in the registered order)

| clause | result | margin |
|---|---|---|
| **ACOUSTIC-MEDIATED point** (§3): rate diff ≥ +0.10 **and** raw diff ≥ 6 | **MET** | rate +0.9062 vs floor +0.10 — clears by **+0.8062**; raw +29 vs floor 6 — clears by **+23** |
| **ACOUSTIC-MEDIATED CI-gated** (§6, authoritative): point met **and** CI lower bound > 0 | **MET** | CI low **+0.8125** vs the 0 gate — clears by **+0.8125**; the entire CI lies above +0.81 |
| **KEY-ONLY-MATCHING point** (§3): \|rate diff\| ≤ 0.03 | **not met** | \|+0.9062\| vs ceiling 0.03 — over by **+0.8762** |
| **KEY-ONLY-MATCHING CI-gated** (§6): entire CI ⊂ [−0.03, +0.03] | **not met** | failed on the point estimate before the CI was consulted; the CI is disjoint from the band by **+0.7825** at its nearest edge |
| **INCONCLUSIVE-TRAP** (otherwise) | not reached | — |

This is not a marginal verdict and it is not a threshold artifact. **Every registered floor is
cleared by roughly an order of magnitude**, the CI is nowhere near either gate, and the
equivalence branch fails by a factor of thirty. The registered instrument was designed to
resolve a difference of six samples out of a denominator it could not know in advance; it
returned a difference of twenty-nine out of thirty-two.

**The control returned an exact zero.** Not one of the 32 cross-percept rows emitted its
appended trap, across 49 flown V2 entries drawn from 31 distinct donor samples. The capture
detector is the *same code path* on both arms — same normalization, same exact-match test,
same per-row trap list — so a 29-vs-0 split cannot be a detector asymmetry. It is also the
strongest available evidence that the core is not simply emitting roster items opportunistically:
supplied wrong values with no acoustic relation to the audio being heard are ignored completely.

---

## 3. Per-sample capture table

The 32 usable samples in full (V1 K, V1 capture, V2 capture, V1 induced substitutions). V2 K is
length-matched to V1 K on every row, so it is not repeated.

| sample_id | K | V1 | V2 | V1 induced subs |
|---|---|---|---|---|
| `slurp:devel:000115:audio-1495375974` | 1 | CAPTURED | no | 0 |
| `slurp:devel:000943:audio-1434529860-headset` | 1 | no | no | 0 |
| `slurp:devel:002992:audio-1489152746` | 1 | CAPTURED | no | 1 |
| `slurp:devel:004604:audio-1501759214` | 1 | CAPTURED | no | 0 |
| `slurp:devel:005028:audio-1502893878-headset` | 2 | CAPTURED | no | 1 |
| `slurp:devel:005359:audio-1497265137-headset` | 1 | CAPTURED | no | 0 |
| `slurp:devel:005453:audio-1490183633-headset` | 1 | no | no | 0 |
| `slurp:devel:005518:audio-1490203960` | 1 | CAPTURED | no | 0 |
| `slurp:devel:005567:audio-1497359684` | 2 | CAPTURED | no | 1 |
| `slurp:devel:005684:audio-1498577434` | 1 | CAPTURED | no | 0 |
| `slurp:devel:005770:audio-1495377172` | 1 | CAPTURED | no | 0 |
| `slurp:devel:006603:audio-1502101512` | 3 | CAPTURED | no | 0 |
| `slurp:devel:006751:audio-1501773837-headset` | 1 | CAPTURED | no | 0 |
| `slurp:devel:007541:audio-1490202471` | 1 | CAPTURED | no | 0 |
| `slurp:devel:007653:audio-1497438989-headset` | 2 | CAPTURED | no | 1 |
| `slurp:devel:007852:audio-1494416109-headset` | 1 | no | no | 0 |
| `slurp:devel:008014:audio-1500899290` | 1 | CAPTURED | no | 0 |
| `slurp:devel:008047:audio-1498570919` | 2 | CAPTURED | no | 1 |
| `slurp:devel:009340:audio-1497882818-headset` | 1 | CAPTURED | no | 0 |
| `slurp:devel:009518:audio-1495734594-headset` | 1 | CAPTURED | no | 0 |
| `slurp:devel:009733:audio--1505407176` | 2 | CAPTURED | no | 0 |
| `slurp:devel:010732:audio-1490184504` | 2 | CAPTURED | no | 1 |
| `slurp:devel:011654:audio-1501692977-headset` | 1 | CAPTURED | no | 0 |
| `slurp:devel:011693:audio-1498565017-headset` | 2 | CAPTURED | no | 0 |
| `slurp:devel:012076:audio-1501766742-headset` | 1 | CAPTURED | no | 0 |
| `slurp:devel:012478:audio-1498486426` | 2 | CAPTURED | no | 1 |
| `slurp:devel:012654:audio-1497860426-headset` | 2 | CAPTURED | no | 0 |
| `slurp:devel:013281:audio-1490354296-headset` | 3 | CAPTURED | no | 0 |
| `slurp:devel:014173:audio-1490291441` | 1 | CAPTURED | no | 0 |
| `slurp:devel:014657:audio-1499695487` | 2 | CAPTURED | no | 0 |
| `slurp:devel:015632:audio-1490021137-headset` | 3 | CAPTURED | no | 0 |
| `slurp:devel:016653:audio-1494513016` | 2 | CAPTURED | no | 1 |

**Capture by trap count** — an unregistered descriptive with no clause attached, recorded
because it is monotone:

| K | usable samples | V1 captured | rate |
|---|---|---|---|
| 1 | 18 | 15 | 0.833 |
| 2 | 11 | 11 | **1.000** |
| 3 | 3 | 3 | **1.000** |

All three non-capturing samples (`000943`, `005453`, `007852`) sit at K = 1, the minimum dose.
**Every sample offered two or more of its own mishearings took at least one.** This is a
dose–response shape, not a threshold, and it is exactly what a matching process that consults
the acoustic percept would produce; it is descriptive only (n = 11 and n = 3 in the upper
cells) and no clause rests on it.

### The 28 excluded samples, with the reason each was excluded

| reason | n | sample ids |
|---|---|---|
| A0 emitted **no wrong value at all** (nothing to harvest) | **5** | `000444`, `005536`, `005743`, `012667`, `017009` |
| **every** harvested candidate equalled a gold slot value of its own target sample and was dropped by the fail-closed gold zero-overlap check | **23** | `001637`, `002120`, `003121`, `003309`, `004134`, `005025`, `005108`, `005541`, `005943`, `007374`, `008072`, `010162`, `010186`, `010545`, `011503`, `012253`, `013795`, `014263`, `014397`, `015258`, `015375`, `015805`, `016825` |

A further **11 samples had some candidates dropped but retained at least one** and are in the
usable 32. In total the gold zero-overlap check removed **42 of 91 harvested V1 candidates**
across **34 samples** (and 8 candidates on V2), leaving 49 flown entries per arm.

---

## 4. The K = 0 starvation caveat — what 28/60 exclusions do to representativeness

This is the load-bearing limitation of the read and it must travel with the verdict.

**The exclusion is overwhelmingly legality-driven, not data-driven.** Only 5 of 60 samples
failed to produce a trap because the core emitted nothing wrong; the other 23 were emptied by
the preregistration's own hard rule that no appended entry may equal, post-normalization, any
gold slot value of its target sample. That rule exists because a trap that *is* the gold value
tests nothing and would breach the gold-free supply rule. It is correct and it was enforced
fail-closed at binding time, three times over. But it is also a **selection operator on the
trap population**, and it selects in a specific direction.

**What it selects for.** A surviving V1 trap is a value the core produced *from this audio* that
matches **no** gold slot of this sample under any type. That is a genuine misperception — the
purest possible instance of "the core's own percept, and it is wrong." A wiped-out sample is one
where every value A0 got "wrong" nevertheless coincided with some gold value of that sample,
i.e. the error was a type misassignment or slot-routing failure rather than a mishearing. The
denominator of 32 is therefore **enriched for samples where the core genuinely misheard**, and
depleted of samples where its A0 errors were gold-adjacent.

**Direction of the bias, stated plainly.** For the question actually asked — does the core
re-commit to its own acoustic percept when that percept is handed back as a legal roster entry —
the retained population is the *maximally trap-like* one. The excluded 23 are precisely the
samples where a self-percept trap would have been least distinguishable from correct supply and
where capture would plausibly have been lower, or would not even have been a harm. **So the
0.9062 capture rate is an upper-leaning estimate of a population rate**, and must never be
narrated as "the core re-commits to its own mishearing 90 % of the time on SLURP devel."

**What survives the bias.** The verdict itself does, by a wide margin, under the most adverse
assumption available. Suppose every one of the 28 excluded samples would have shown **zero**
V1 capture, and score the whole 60:

| adverse-case population reading | value |
|---|---|
| capture(V1) over all 60 | 29 / 60 = **0.4833** |
| capture(V2) over all 60 | 0 / 60 = **0.0000** |
| rate difference | **+0.4833** vs the +0.10 floor |
| raw difference | **+29** vs the floor of 6 |

Even in that worst case the ACOUSTIC-MEDIATED point thresholds clear by **+0.3833** and **+23**.
**No plausible reweighting of the excluded stratum can flip the sign or the verdict** — the
control arm's exact zero makes the difference robust to any assumption about the missing 28,
because the excluded samples can only reduce V1 capture, never raise V2's. The *magnitude* is
what the exclusion compromises; the *existence and direction* of acoustic mediation is not
in reach of it.

**A second, subtler consequence.** The 42-candidate drop means the trap supply is much sparser
than the 91-value harvest implies, and the K distribution tops out at 3 against a cap of 5. The
dose–response in §3 is therefore measured over a compressed range. A successor wanting a
population-representative capture rate would need a legality-compatible way to keep the
gold-adjacent stratum in the denominator — for example by scoring "trap emitted" against a
non-gold-derived reference — and that is a fresh registration, not a re-cut of this one.

---

## 5. SLU-F1 guardrail, induced substitutions, and the harm reading

Registered guardrails (§3), descriptive, no clause attaches. Cited comparator: the consumed
P-SLU A3 arm's official pooled SLU-F1, `0.5961280580450439`, pinned in the suite as
`CONSUMED_A3_SLU_F1` and taken verbatim from `2026-08-18-pslu-read/verdict.json`.

| arm | SLU-F1 (pooled over all 60 rows) | Δ vs cited A3 | parse rate | empty rate | induced subs |
|---|---|---|---|---|---|
| cited **A3** (consumed, no traps) | **0.5961** | — | — | — | — |
| **V1** self-percept | **0.5003** | **−0.0958** | 1.0000 | 0.0000 | **11** |
| **V2** cross-percept | **0.5907** | **−0.0054** | 1.0000 | 0.0000 | **3** |

**Trapping costs task quality, and only self-percept trapping does.** V2 appended exactly as
many entries, from the same source distribution, at the same lengths, and cost **−0.0054** —
inside noise. V1 cost **−0.0958**. The roster-size confound is therefore controlled: the damage
is not from making the roster longer, it is from the *content* being this audio's own
mishearing.

**The arm-level number understates the per-sample damage.** SLU-F1 here is pooled over all 60
rows per arm, and 28 of those rows carry no trap at all — on those rows V1 and V2 are the same
plain A3-form request. The entire −0.0958 is generated by the 32 trapped samples, so the cost
*where a trap exists* is materially larger than the arm figure. A subset SLU-F1 over the usable
32 was **not** computed by the registered suite and is **not** claimed here; the point is only
that −0.0958 is a diluted floor on the effect, not a measure of it.

**Induced substitutions localize the harm precisely.** Of V1's 11, exactly **8 fall on usable
samples** and **3 fall on excluded (K = 0) samples**. Of V2's 3, **0 fall on usable samples** and
the same **3 fall on the same three excluded samples** (`005743`, `014263`, `015375`). Those
three ids are K = 0 on both arms, so their V1 and V2 requests are identical constructions — and
they produced identical induced-substitution counts, an incidental but clean in-read determinism
check. Netting the shared baseline out: **the trap channel induced 8 substitutions on V1 and 0
on V2, over the same 32 samples.**

**Capture is not the same as damage, and the gap is informative.** 29 samples captured a trap;
only 8 of them registered an induced substitution — i.e. **21 of 29 captures emitted the trap
without displacing an aligned gold filler**, landing in a slot type absent from gold or where
the aligned reference was itself a roster value. Self-percept contamination is therefore
*ubiquitous* (90.6 % of trapped samples) but *selectively costly* (28 % of captures displace
correct content). Both halves matter for the deployment reading: a control plane that leaks the
core's own prior mishearings back into its evidence roster will see them re-emitted almost
always, and will lose gold content roughly a quarter of the time it happens.

**Instrument integrity.** Parse rate 1.0000 and empty rate 0.0000 on both arms — no degenerate
rows anywhere. `recheck_mismatch_count = 0`: every per-sample TP/FP/FN reproduced the committed
frozen scorer exactly on recheck. `harness_defect_reasons` empty. Flight status `COMPLETED`,
error `None`, 60/60 rows on each arm with 120 distinct (arm, sample_id) pairs.

---

## 6. Why this is not the "it would have said that anyway" artifact

The strongest alternative explanation of a 90 % capture rate is deflationary: the V1 traps came
from *this* audio, so they are lexically what the core tends to produce for this audio, and it
would emit them with or without the roster. The design already answers this, from two directions.

**The consumed baselines rule it out.** With no supply at all the core scores **0.1741** SLU-F1
on these same 60 samples (P-SLU A0, reproduced bit-identically by P-KEY's AUD-NOSUP arm across
sessions — cited, not recomputed here). With the plain legal roster it scores **0.5961** (A3).
The roster therefore *moves the core off* most of its A0 percept: supply repairs the
misperception. V1 then re-supplies that abandoned percept, rendered in the roster's own item
shape, and the core **takes it back on 29 of 32 samples** and loses ~0.096 pooled SLU-F1 doing
so. The core does not merely persist in an error it was going to make — it *reverses* a
correction it had already made, when the error is re-presented as legal evidence.

**V2 rules out the roster-mechanics explanation.** If the effect were "the core emits appended
entries because appended entries are salient," V2 would capture too. It captured zero. The
appended-entry position, count, rendering, length distribution, and source distribution are
identical across arms. The **only** difference is whether the appended value came from this
sample's audio or another's.

Together these close the loop the registration was built to close: **supply-use matching
consults the acoustic percept.** That is a positive mechanism finding about the speech channel's
participation in USE, established on a frozen core with zero parameter change.

Two honest limits on it. First, the mechanism is demonstrated *on the harm side*: what has been
shown is that the audio channel governs which supplied item gets matched, and the demonstration
consists of the core matching a wrong item. Nothing here shows the same acoustic mediation
delivering *benefit* — that is P-KEY's question and P-KEY did not resolve it (§7). Second,
"acoustically mediated" is the registered verdict's own language and means the matching is
sensitive to the audio; it does not identify *what* about the audio (phonetic similarity,
prosodic alignment, or a coarser this-audio-vs-that-audio discrimination). The design cannot
distinguish those, and no such refinement is claimed.

---

## 7. What this adds to P-KEY's INCONCLUSIVE on the speech term

P-KEY returned **INCONCLUSIVE-KEY**: I = Δ_AUD − Δ_TXT = **+0.0463**, 90 % CI
**[−0.0033, +0.0970]**, point estimate inside the registered dead zone between the 0.03
equivalence ceiling and the +0.06 speech-term floor, with ~89 % of the supply benefit realized
text-side (Δ_TXT = +0.393 against Δ_AUD = +0.440). Its own §7 named P-TRAP as the mechanism
complement that "attacks the question from the self-percept side rather than through a
difference-of-differences at n = 60."

**P-TRAP does not fire P-KEY's clauses and cannot.** They measure different quantities: P-KEY's
I is a *net task-quality benefit* interaction on a partial-credit metric; P-TRAP's capture
difference is a *mechanism-presence* measurement on the matching step. §2b remains formally open
on P-KEY's own terms, and nothing here re-opens or re-cuts P-KEY's registered thresholds.

**What P-TRAP does change is which explanations of P-KEY's null remain available.** The
deflationary reading of a text-side-dominant benefit was that *the audio is only a retrieval
key* — that the core transcribes once, then does all roster matching text-side against its own
transcript, with the acoustic signal playing no further part. **That account is now falsified as
a general description of matching.** If matching were text-side, a wrong value with no acoustic
relation to this audio would be no less matchable than one with — the V2 entries are the same
kind of text, in the same position, at the same length. They captured **0/32** against V1's
**29/32**. Matching consults the audio.

The two results are therefore consistent and jointly narrower than either alone:

- **The speech channel participates in supply USE** (P-TRAP, CI-gated, margin ≈ 8× the floor).
  Not a key; a live discriminator at match time.
- **Its measured net contribution to task quality remains unresolved** (P-KEY, I = +0.0463, CI
  crossing zero, dead-zone point estimate). Participation is not benefit.
- **The one place the participation has been *measured* rather than inferred, it is a cost**
  (P-TRAP guardrail: −0.0958 pooled SLU-F1, 8 induced substitutions on the usable set against
  V2's 0). The speech channel's demonstrated reach into USE is, on this evidence, a
  contamination pathway.

There is a real tension worth stating rather than smoothing: acoustic mediation of matching is
strong and unambiguous (Δ = +0.906), while the audio's net benefit over its own transcript is
small and uncertain (I = +0.0463). The reconciliation the evidence supports is that **the
acoustic percept is consulted at match time, but on this carrier the core's own transcript
already carries nearly all of the information that consultation uses** — P-KEY measured a
53.6 % macro-WER self-transcript costing essentially nothing at baseline (−0.0001) and +0.046
under supply. Acoustic mediation being demonstrable does not make it *worth* much here, and
P-TRAP shows it is demonstrable precisely by making it *cost* something. That reconciliation is
a reading, not a measurement, and it is offered as such.

**Effect on §2b of the qualification draft.** §2b stays **OPEN** and the freeze stays **HELD** —
P-TRAP was never a §2b decision instrument and does not become one. What §2b may now record as
settled is a genuinely new line: the speech-term question has an **affirmative mechanism-side
answer** (matching is acoustically mediated, CI-gated, on the SLURP carrier) sitting next to an
**unresolved benefit-side answer** (P-KEY's dead-zone I). The honest §2b framing is no longer
"speech knowledge participates, or the audio is only a key" — the second disjunct is dead. It is
"speech participation in USE is established; its net value in the supply loop is not."

**A new USE-side risk is citable at discovery tier**, and belongs beside C2's harm channel and
C5's deployment reading: **self-percept contamination**. If a control plane's evidence roster
can contain the core's own earlier outputs on the same audio — which any pipeline with a
recall/caching/self-supply stage can produce by accident — the core re-commits to those values
at 0.9062 on the trapped population, reversing repairs the legal roster had already made, and
displaces gold content on 28 % of the captures. The mitigation this implies is an ORG-side
provenance rule (never re-supply the core's own prior emissions for the same episode), and the
control that makes it checkable is the V2 construction. Scope: one carrier, n = 32 usable,
single run, same-distribution, an enriched trap stratum per §4.

No superiority, generalization, deployment, or paper-scale claim attaches to any number in this
document.
