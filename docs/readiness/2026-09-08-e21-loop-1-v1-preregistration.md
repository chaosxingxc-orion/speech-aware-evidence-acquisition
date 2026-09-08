# E21-LOOP-1 — the first whole-loop Earnings-21 cell (v1 preregistration)

**Status: PREREGISTERED, MODEL-FREE PREPARATION COMPLETE, FLYABLE ON THE SLURP LINE'S
COMPLETION.** Owner Decision 12-G of 2026-09-08 is the GO for this preparation and fixes the
sequence: the cell flies after the SLURP line. Nothing in this note is an authorization to
contact the core today, and nothing in it decides anything: the numbers below are an
instrument's precision and a budget, never a result.

Exposure row `SAEA-E21-MF-LOOP-1-PREP-V1` (`model-free-check`) covers every read this note
rests on. **Zero model, GPU, server, socket, tokenizer, tool, embedder, network, audio-decode
and paid-API contacts.**

| | |
|---|---|
| experiment fragment | `configs/experiment/e21-loop-1-v1.json` |
| arm | `configs/baseline/e21-loop-1-relisten-repair.json` |
| form twin | `configs/baseline/e21-loop-1c-random-flag-twin.json` |
| dataset fragment | `configs/dataset/earnings21-discovery-conec-names.json` |
| comparators | `SAEA-E21-FULL44-DIRECT-BASELINE-V2` (sealed) and `SAEA-E21-KC-E1F-REPAIR-44-V1` (sealed) |
| judge receipt | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-loop-1-judge-inventory/` |
| wire check | `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-loop-1-wire-check/` |
| design | `docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md` §5 |

---

## 1. The cell, as the four agents

This is the design note's whole loop, on Earnings-21, for the first time. Every previous
Earnings cell ran a proper subset of it.

| agent | what it does here | seam |
|---|---|---|
| **Planner** | meeting task → fixed 90-second windows as the transport, the capped ConEC brief as the knowledge view, one core call per FLAGGED window, stop after one revise | the hash-pinned selective plan and the two declaration blocks on the baseline fragment |
| **Observer**, pass 1 | none: the sealed comparator's own per-window hypothesis is supplied through the KC-E1f predecessor binding | `core.predecessor_snapshot` |
| **Reviewer** | two registered gold-free judges score and flag spans of that sealed draft: `e21-brief-name-near-miss-v1` and `earnings-numeric-format-flag-v1` | `core.base.JUDGES` |
| **Observer**, pass 2 | **selective re-listen**: for a flagged window only, a re-cut of that window — the union of its flagged spans widened by **+5.0 s on each side** and floored at **10.0 s**, clamped to the window | `analysis.e21_relisten_plan`, cut by the base policy's own `reproduction.obs_audio.encode_slice` |
| **Solver** | the frozen `e21-entity-repair-substitutions-v1` rule over the re-cut span's own pass-1 words, at one contact per flagged window | `reproduction.repair_loop` |
| **Planner**, commit | an unflagged window delivers its predecessor verbatim and spends nothing; the call's stitch is every window, in order | the hook's back-fill |

**Read against KC-E1f, one factor moves: the Reviewer plus the selective re-listen.** KC-E1f
repaired every one of the 1,593 windows, each with the whole 90 seconds and the whole
window's pass-1 text. Everything else — the arm, the policy, the evidence source, the cap-12
brief, the predecessor binding, the repair frame, the delivery rule and its three parameters,
the task instruction, the scorers, the OBS protocol and the batch geometry — is byte for byte
KC-E1f's, and the wire check asserts it (§8).

### 1.1 Why the speaker-turn units are not the transport, and are not the Reviewer's context either

The brief this cell was written from left the question open. It is answered from the OBS-E1
PERSON harm decomposition's own numbers
(`docs/readiness/2026-09-08-e21-obs-e1-person-harm-decomposition-v1.md`), and the answer is
**no, on both counts**:

* the speaker-turn transport is REJECTED (OBS-E1: corpus WER +1.0487 but PERSON −2.0912), and
  nothing here re-opens it;
* the decomposition's §3 shows the harm **is duration**, monotone with no exception — under
  3 s −14.545, 3–5 s −5.469, 5–10 s −5.656, 10–30 s −2.541, 30–60 s −0.397, and at 60 s or
  more the units are BETTER by seven errors (+0.861). Units under 10 s hold 23.3 % of the
  PERSON words and **78.7 % of the harm**;
* the cut essentially never goes **through** a name: 1 of 656 multi-word PERSON mentions is
  split by a unit boundary, against the comparator's 4. So a unit boundary is not a location
  where names break, and a Reviewer told "look near a unit edge" would be told to look
  where short units are, which is a duration signal wearing a boundary's clothes;
* the decomposition's own tip commit says both properties the OBS-E1 verdict named from
  call-level tertiles **invert or vanish at the unit grain**, and that a successor transport
  rule must be built on the unit-grain table. That table is closed but it is a table about a
  transport, not about where to look inside a window.

The units therefore enter this cell in exactly one way: as the **evidence for the two
observation constants** below. They are not a transport, not a context source and not a
prior.

### 1.2 The margin and the floor, and where each number comes from

| constant | value | source |
|---|---|---|
| context margin, each side | **5.0 s** | the decomposition's §5 prices +3 / +5 / +10 s; the coordinator's direction of 2026-09-08 fixes at least +5 |
| minimum re-listen length | **10.0 s** | the same direction's refusal-to-shrink rule, and the duration ladder that motivates it |

**The floor is stated with the objection it does not answer.** A 10-second unit sits in the
5–10 s band the decomposition measured at **−5.656** PERSON points *as a transport*. This is
not a transport: the whole call is still tiled by the comparator's own 90-second windows, the
core is given the re-cut span's own pass-1 text as conditioning, and the delivery rule can
only substitute inside that span. But the risk is real and is priced by the twin (§4) and
named as this cell's first fallback (§10): if E21-LOOP-1 fails, the first successor raises the
floor to 30 s (the −0.397 rung) before anything else is changed.

## 2. The Reviewer, priced model-free before it is flown

Receipt: `docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-loop-1-judge-inventory/judge-receipt.json`.
Zero contacts. The instrument is the sealed comparator's own 1,593 per-window drafts,
recovered — never re-derived — through `analysis.e21_window_pairing`, and the truth is the
ConEC alignment that same instrument charges to each window.

**The identity anchor cleared before any precision was computed**, 10 of 10 checks: 1,593
windows over 44 calls, S/D/I 13,098 / 5,701 / 10,700 over 359,765 reference words, PERSON
22.489 % over 2,917 tagged words and ORG 17.213 % over 4,363 — the comparator's own sealed
figures to the digit.

**The truth set**: a PERSON/ORG **substitution** — an alignment operation whose reference word
carries a PERSON or ORG entity id. There are **1,253** of them, spread over **674** of the
1,593 windows, plus **154** PERSON/ORG deletions which are reported and are *not* in the
recall denominator: a deletion consumes no hypothesis word, so no span-based judge reading a
draft can point at one. Insertions never reach an entity bucket at all.

### 2.1 `e21-brief-name-near-miss-v1`, at seven bands

Flagged-window share, span precision (a flagged span contains a real PERSON/ORG substitution)
and two recalls: span recall (the substitution is *inside* a flagged span) and **window
recall** — the share of PERSON/ORG substitutions that sit in a window the judge flagged, which
is the loop's own ceiling, because the Solver hears the whole re-cut and is shown its whole
word range.

| `max_distance` | flagged spans | flagged windows | share of 1,593 | span precision | window precision | span recall | **window recall** |
|---:|---:|---:|---:|---:|---:|---:|---:|
| **0.10** | 100 | 86 | 5.40 % | 49.00 % | 80.23 % | 3.99 % | **14.37 %** |
| **0.15** | 385 | 270 | 16.95 % | 21.30 % | 58.15 % | 6.78 % | **27.13 %** |
| **0.20** **(flown)** | 912 | 534 | 33.52 % | 15.24 % | 53.00 % | 11.65 % | **47.57 %** |
| **0.25** | 2021 | 892 | 55.99 % | 8.31 % | 47.20 % | 14.21 % | **66.08 %** |
| **0.30** | 3053 | 1139 | 71.50 % | 6.22 % | 45.65 % | 15.96 % | **79.25 %** |
| **0.35** | 4530 | 1322 | 82.99 % | 4.72 % | 44.10 % | 17.96 % | **87.95 %** |
| **0.45** | 19503 | 1576 | 98.93 % | 1.61 % | 42.58 % | 26.26 % | **99.60 %** |

### 2.2 The other two judges, measured rather than assumed

`earnings-numeric-format-flag-v1` fires on **87 of 1,593 windows (5.46 %)**, 123 spans, and
its span precision against PERSON/ORG substitutions is **0.0** — as it should be: it asks a
numeric question, not a name question. It is kept in the inventory because a malformed figure
is a second reason to hear a window again, and its base rate is small enough that it costs
about five per cent of the budget. Its own precision against a numeric-accuracy miss is not
measured here and is not claimed.

`e21-substitution-alignment-flag-v1` fires on **0 of 1,593 windows**. That is not a defect and
it is why the measurement was worth making: on a pass-1 draft its predecessor *is* the draft,
so it can only report a perfect alignment. It belongs **after** the Solve, where its refusal
table is the delivery ledger, and that is where this cell places it — as a reported covariate,
never as a flag source. WAVE W1 §5 listed exactly this as "still to measure".

### 2.3 The operating point, chosen by a rule that uses no gold

The band is a knob and the receipt above is a table of what it buys. **The rule was fixed on a
gold-free quantity and applied to it**: the operating point is the **largest `max_distance` on
the declared ladder whose flagged-window share is at most 50 % of the windows** — the budget
ceiling the decision rule in §6 requires. Flagged-window share needs no reference transcript,
no alignment and no gold of any kind; it is a property of the draft and the brief. The
precision and recall columns played no part in the choice and are published so a reader can
see what the choice cost.

That rule selects **`max_distance` = 0.20**. The numeric judge adds at most its own 5.46 % on
top, so the inventory's share is bounded by 38.98 % before it is measured; the pinned plan
measures it exactly at **600 units, 37.66 %** of the 1,593 windows (§3).

**What that band buys, stated in the two numbers that matter.** At 0.20 the near-miss judge
flags a third of the windows, a flagged WINDOW carries a real PERSON/ORG substitution
**53.00 %** of the time, and the flagged windows contain **47.57 %** of the whole substitution
mass. So a third of KC-E1f's contacts can reach about half of what KC-E1f could reach — which
is the arithmetic the cell's non-inferiority clause is a bet on, and which the flight either
confirms or does not.

**What this is not.** It is not a claim that 0.20 is the best band. Span precision falls
monotonically from 49.0 % at 0.10 to 1.6 % at 0.45 while window recall rises from 14.4 % to
99.6 %, which is the ordinary shape of a detector's trade; a cell that wanted precision would
fly 0.10 at 5.4 % of the budget and 80.2 % window precision, and reach a seventh of the mass.
The choice is the budget's, and the budget is the decision rule's.

## 3. The plan, and why it is data

| | E21-LOOP-1 | the twin | KC-E1f | the sealed comparator |
|---|---:|---:|---:|---:|
| plan | `docs/receipts/obs/e21-relisten-plan-v1.json` | `…/e21-relisten-twin-plan-v1.json` | — | — |
| contacts, one pass | **600** | **600** | 1,593 | 1,593 |
| share of KC-E1f's contacts | **37.7 %** | 37.7 % | 100 % | 100 % |
| delivered audio, one pass | **15,340.5 s** | 15,340.5 s | 141,345.85 s | 141,345.85 s |
| share of KC-E1f's audio | **10.9 %** | 10.9 % | 100 % | 100 % |
| re-cut seconds — min / median / mean / max | 10.26 / 10.71 / 25.57 / 90.00 | 10.26 / 10.71 / 25.57 / 90.00 | 90 flat | 90 flat |
| units under 10 s | **0** | 0 | — | — |
| units at 60 s or more | 84 | 84 | 1,593 | 1,593 |
| units per call — min / median / max | 1 / 13 / 34 | 1 / 13 / 34 | — | — |
| pass-1 words shown per contact — median / mean | 33 / 67.7 | 33 / 67.3 | the whole window | — |

**The distribution is bimodal and that is the margin doing its job.** A window whose criticism is one
name becomes a 10.3-second re-cut at the floor; a window whose flags are spread across it
becomes most of the window, and 84 units reach 60 seconds or more — the band the harm
decomposition measured as BETTER than the 90-second window. **Not one unit is under the floor.**

**Every roster call carries at least one unit.** The plan builder stops rather than omit a call, and
it did not have to: the thinnest call carries 1 unit(s). That matters because the
policy refuses a call with nothing to re-hear — a call whose stitch would carry no contact at all is
a defect, not a cheap arm.

A re-listen plan is a `saea-e21-relisten-plan-v1` document, hash-pinned in the composed config
and re-proved by the runtime loader on the bytes it actually loads. Its proof obligation is
deliberately **not** a tiling proof — a selective plan covers only the windows the Reviewer
criticised — and is, per call: units in `unit_index` order from 1; one unit per parent window,
in ascending window order; every unit inside its named parent window's own span; every unit at
or above the refusal-to-shrink floor (or exactly its parent, when the parent is shorter); a
non-empty word range inside that window's own pass-1 word count; and no overlap.

**Position in seconds is DERIVED and says so.** Earnings-21 ships no word timestamps — the harm
decomposition checked all 362,747 `ts`/`endTs` cells on these 44 calls and every one is empty
— so a flagged word span is converted to seconds by its window's own local rate (window
seconds ÷ window draft words), the same convention the decomposition uses, and the inverse
conversion brings the re-cut bounds back to a word range, rounded outward so the text the
Solver is shown is never narrower than the audio it hears. It is an attribution, never an
alignment, and both directions use the same rate so they cannot disagree with each other.

## 4. The twin: the same loop, listening in the wrong places

`configs/baseline/e21-loop-1c-random-flag-twin.json` pins a second plan built by the same
script from the same judges' output and **nothing else about it**: per call it takes the SAME MULTISET of re-cut durations the judges' plan produced and places them longest first, each into a uniformly random unused window of that call able to carry it, at a uniformly random offset inside it (seeded RNG, 20260903).

Longest first, and into a window that can carry it, for one reason: a call's last window is
usually shorter than 90 seconds, and a naive draw would quietly clip a long duration into it —
making the twin cheaper than the arm on the one axis it exists to hold fixed. As built, the
twin pays the identical contact count per call, delivers the identical audio seconds per call
and carries the identical re-cut duration multiset per call — and carries none of the
Reviewer's targeting. The wire check asserts all three, on 44 of 44 calls (§8).

**One property of a uniform draw, reported rather than discovered later.** 291 of the twin's
600 windows (48.5 %) happen to be windows the judges also flagged. That is not a leak and not a
bias: with 600 of 1,593 windows flagged, a uniform draw of `k` windows from a call of `N`
coincides `k²/N` times in expectation, and summing that over calls gives a `k`-weighted mean of
the per-call flagged fraction — necessarily above the pooled 37.7 %. The consequence for
reading the result is asymmetric and should be stated in the verdict: **a positive twin leg is
strong evidence for targeting; a null twin leg is weak evidence against it**, because the twin
is already on target about half the time.

**What the twin separates.** Two things could produce a gain over KC-E1f: hearing a narrower
span again at all, and hearing the RIGHT narrower span. The comparator pair prices the first.
The twin prices the second. If the arm's PERSON gain survives against the twin, the Reviewer's
targeting bought it; if it does not, the second look did, and the judges are an expensive way
to pick windows at random.

## 5. Roster, pairing, estimator — all unchanged

Not one of these moves from KC-E1f, the null replicate or the sealed comparator, and that is
deliberate: a cell whose estimator moved could not be read against them.

* **Roster**: all 44 `earnings21-original` discovery calls, split identity
  `fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e`. No draw.
* **Pairing unit**: the fixed 90-second window, 1,593 of them. **Every window is delivered by
  both arms** — a flagged one repaired, an unflagged one from the predecessor — so the paired
  read is over the same 1,593 units as KC-E1f's, not over the contacted subset.
* **Bootstrap cluster**: the call, 44.
* **Estimator**: the pooled ratio through
  `analysis.paired.resampled_statistic(cluster_of=analysis.e21_window_pairing.call_of)`, seed
  **20260903**, **10,000** replicates, **CI90**, reported under both weightings (natural
  mixture and equal stratum).
* **Scoring**: one pass of `core.scoring_batch` over each complete manifest, five declared
  scorers, never sharded.

## 6. The decision rule, fixed before the flight

Signed so that a POSITIVE value means fewer errors.

### 6.1 Primary

> **ADMITTED** iff the call-clustered CI90 **lower bound** on the PERSON entity-WER reduction
> (sealed comparator − E21-LOOP-1) is **> 0**, AND the cell is **non-inferior to KC-E1f** at
> the margin this carrier measured for itself — `LB(E21-LOOP-1 − KC-E1f) >= −0.25009` — AND
> the realized **core calls are at most 50 % of KC-E1f's 1,593**, AND every gating guard in
> §6.3 holds.
>
> **ADMITTED AS AN IMPROVEMENT** if, in addition, `LB(E21-LOOP-1 − KC-E1f) > 0`.
>
> **NULL** if the primary lower bound includes 0 while every guard holds.
>
> **REJECTED** if any gating guard fails, with the failing guard named and the per-class table
> published either way.

The margin **0.25009** is the half-width of `SAEA-E21-FULL44-NULL-REPLICATE-V1`'s own
call-clustered CI90 on ConEC PERSON entity WER, and its null interval is
`[−0.24338, +0.25680]` (that cell's §3). It is a number another cell measured on this carrier
under a null in which nothing was changed, and it predates this contrast.

**Reported beside the primary, not gating**: whether the PERSON effect's interval is disjoint
from that null interval, stated explicitly rather than left to a reader to divide.

### 6.2 The attribution leg

`LB(E21-LOOP-1 − twin) > 0` on PERSON. **Gating for the CLAIM, not for the admission**: if
this leg's interval includes zero the cell may still be ADMITTED on §6.1, and the verdict may
then say the loop helped but **may not say the Reviewer's targeting is why**.

### 6.3 Guards, all non-inferiority at this carrier's own measured margins

| # | guard | rule | margin | source |
|---|---|---|---:|---|
| 1 | delivery integrity | every window's delivered text equals its sealed predecessor outside the accepted substitution spans, with the identical whitespace-token count; a construction check that ABORTS the read on failure | — | construction |
| 2 | window coverage | every one of the 1,593 windows is delivered exactly once, contacted or back-filled; a construction check that ABORTS the read | — | construction |
| 3 | corpus WER | `UB(E21-LOOP-1 − comparator) <= +0.05793` | 0.05793 | null verdict §3 |
| 4 | numeric-value accuracy, call-pooled | `LB(E21-LOOP-1 − comparator) >= −0.15651` | 0.15651 | null verdict §3 |
| 5 | over-generation, insertions per reference word | `UB(E21-LOOP-1 − comparator) <= +0.02218` | 0.022178 | the KC-E1f v2 re-decision §4, computed from the null replicate's own per-window rows |
| 6 | negation-critical / semantic high impact | advisory, gates nothing | — | the null's own interval excludes zero, so the clause is unanswerable on this carrier (v2 re-decision §2.3) |

Guards 1 and 2 gate by construction; 3, 4 and 5 gate statistically; 6 does not gate.

### 6.4 Core-pressure covariates, reported by the verdict

Not decision criteria. Core calls per window and per call; prompt and completion tokens per
contact and in total; delivered audio seconds; **judge interceptions** — flags raised, windows
flagged, flags that led to an accepted substitution; **re-listen count** and the realized
re-cut duration distribution; **rejected revisions by class** (`unbalanced_replace`,
`deletion`, `insertion`, `oversized_replace`) and refusals by reason; windows delivered
unchanged; and the share of the final transcript the control plane delivered rather than the
core produced.

## 7. Budgets and the serving geometry

| | per cell | both cells | basis |
|---|---:|---:|---|
| core calls | 600 realized, **720** planned | **1440** | the exact unit count of the pinned plan × 1.2 retry headroom |
| speech audio seconds | 15,340 realized, 18,409 planned | **37,000** registered | the plan's own delivered seconds × 1.2, rounded up |
| GPU hours | between **0.120** (audio-proportional) and **0.418** (contact-proportional) | **0.7** planned, 1.0 stop | KC-E1f's realized 1.1093 GPU-h for 1,593 contacts over 141,345.85 s, scaled both ways |
| paid API | 0 | **0** | in force |

**The contact figure is not an estimate.** It is the number of units in the hash-pinned plan, which
the wire check reads back out of the composed config, so a plan edited after this note was written
would change the pin and refuse to load.

**The geometry is projected, and a prompt fit decides it.** KC-E1f flew
`q4km-e21-buf90-mmproj-gpu-04ccc72a-np4` — four 9,216-token slots at a 36,864-token context —
because its worst realized request was 3,504 tokens (margin 2.630 against the study's 2.0
rule). Every one of this cell's requests is strictly smaller than that cell's: the audio is a
re-cut instead of the full 90 seconds, and the pass-1 text is a sub-span instead of the whole
window; only the cap-12 brief is unchanged. The projection is therefore that the np6 fragment
(six 6,144-token slots at the same context) satisfies the margin rule with room. **It is a
projection and it does not decide anything**: a prompt fit in SERVER mode, under this cell's
own exposure row, measures the realized worst request before the first flight contact and the
geometry follows lever 1 of that fit's own pre-fixed procedure, exactly as KC-E1f's did.

## 8. What has been proved model-free, and what has not

`scripts/e21_loop_1_wire_check.py`, receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-loop-1-wire-check/`. Zero
contacts, zero sockets.

**RESULT PASS, zero failures.** Four halves:

| half | what it proved |
|---|---|
| `config` | both cells COMPOSE. Arm config hash `58f175b796076a2d…`, protocol hash `504e61aa0b16799d…`; twin config hash `f9437a9deac0a123…`, protocol hash `1868bcb3423d690c…`; both against split identity `fcc1b0bc…d69e`. The arm's baseline fragment differs from **KC-E1f's** in exactly `obs_unit_plan`, `obs_unit_plan_sha256`, `window_review`, `window_observe` — the one factor — and from the **twin's** in exactly the same four. The serving geometry is reported as a SEPARATE named difference (np6 projected against KC-E1f's np4), never folded into the one-factor claim |
| `plan` | both plans load through the real `reproduction.obs_loop` loader and are re-proved on the bytes actually loaded; both cover 44/44 roster calls; the arm's `window_review` / `window_observe` values EQUAL the plan document's own `flag_source`, `context_margin_seconds`, `min_relisten_seconds` and judge list, so a fragment claiming one Reviewer and pinning a plan built by another is refused before any contact; and the twin matches the arm on **contact count and re-cut duration multiset on 44 of 44 calls** |
| `request` | the real `RepairWindowHook` over the real, hash-verified predecessor binding, on four calls: every rendered instruction **ENDS with exactly the plan's word range** of that window's own pass-1 text (an equality on the frame's tail, not a substring search); a fully refused pass 2 rebuilds the sealed comparator's own hypothesis for the call **byte for byte**; and contacted plus back-filled windows equal the call's window count on every one |
| `payload` | the shared `rails.core_client.payload_binding_stage` over the cell's own 44-row roster BINDS |

**The refusal rebuild is the property worth naming twice.** It is the selective loop's version of
KC-E1f's "a useless pass-2 answer costs nothing": if the core answered every re-cut with nothing
usable, this cell would deliver the sealed comparator's transcript, exactly, on every one of the
1,593 windows. The floor of this cell is the comparator, by construction, and it is measured on real
sealed bytes rather than asserted.

**What is NOT proved, and is named rather than left to be discovered.** No contact has been
made, so nothing here says the core will use a re-cut well. The re-listen's own risk — a
10-second window in a band the OBS-E1 decomposition measured as harmful for a transport — is
priced by the twin and by the guards, not by this preparation. And the delivery rule's two
ratios (`min_anchor_ratio` 0.6, `max_substituted_fraction` 0.1) are now computed over the
re-cut span rather than the whole window: the rule is byte-identical and its relative
strictness is unchanged, but in absolute terms it admits about two substituted tokens on a
twenty-five-word span where a hundred-and-eighty-word window admitted eighteen. That is a
consequence of the factor and is a reported covariate, never a knob this cell tunes.

## 9. Claim surface

Discovery data. No superiority claim, no generality claim, no Stage-3 claim, no
`paper-scale-confirmatory` profile, no Earnings-22 contact, no confirmatory read, no knob
tuned on the evaluation ten. The E5 evaluation half carries 342 paired windows, below the
program's `n >= 400` rule, and is reported apart and descriptively with no interval quoted.

KC-E1f's own admission is **provisional and its replication is UNMET**
(`docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v2-redecision.md` §3). E21-LOOP-1 is
therefore measured against it as a **comparator**, never cited as an admitted effect, and this
cell's admission cannot discharge that replication obligation: a different mechanism is not a
second pass of the same one.

## 10. If it fails, what happens next — fixed in advance so it cannot be chosen afterwards

1. **The primary fails, or the cell is non-inferior but not better.** Raise the re-listen floor
   from 10 s to 30 s — the −0.397 rung of the decomposition's duration ladder — changing
   nothing else, and re-fly. The margin and the judge stay.
2. **The primary holds but the twin leg does not.** The gain is the second look, not the
   targeting. The successor drops the judges, keeps the selective re-listen at a random flag
   set of the same size, and the Reviewer returns only when a judge with better window
   precision exists.
3. **A guard fails.** Name it and stop. The v1 KC-E1f verdict is the precedent: a guard failure
   is a result, and the successor is a preregistration, not an amendment.

At most **one** recovery re-registration for this flight, per the 2026-09-03 rules; a second
failure stops the flight and the fix is proven on a 4-row dry run first.

## 11. What this note does not authorize

It is not an owner GO to fly. Decision 12-G authorized the model-free preparation and fixed the
sequence — the SLURP line first. No judge enters any default plan on the strength of this note;
the near-miss judge's admission receipt is the precision table of §2 and nothing more, and
whether ACTING on its flags helps is exactly what this cell is for.
