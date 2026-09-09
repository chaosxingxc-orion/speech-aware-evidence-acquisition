# DR-1: draft with the short speech, refresh with the long speech

**Preregistration. Not a GO, not a registered flight, and not an amendment.**
`SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1` stays REJECTED under its own preregistered rule; KC-E1f's
admission stays provisional with its replication UNMET; OBS-E1b stays prepared and unflown. This
document fixes, before any contact, what DR-1 would send, what it would stitch, what it would be
measured against and what would count as a win — so that if the owner ever says GO, nothing below can
be chosen after seeing a number.

| | |
|---|---|
| what asked for it | owner Decision 13-J, 2026-09-09: *in the Observe stage use the short speech to generate drafts quickly, then in the Plan stage give the model the long speech together with the prior draft and let it refresh the transcript once, systematically* |
| the measurement it acts on | `docs/readiness/2026-09-08-e21-obs-e1-person-harm-decomposition-v1.md` |
| pass 1 | `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1`, attempt `attempt-20260908T150858Z-c597a8` — **sealed, not re-flown** |
| stitch | `saea-e21-unit-draft-majority-overlap-v1` (`analysis.e21_unit_draft_stitch`), proved in `docs/checks/speech-aware-evidence-acquisition/2026-09-09-e21-dr1-unit-draft-stitch/` |
| bindings | `docs/receipts/e21-unit-draft-obs-e1-speaker-turn-units-v1.json` (`40f46695…f241d`) · `docs/receipts/e21-predecessor-full44-direct-baseline-v2.json` (`26f1d9cc…a72a`, KC-E1f's own, unchanged) |
| cells | `configs/experiment/e21-draft-then-refresh-dr1-v1.json` — DR-1c, DR-1f, DR-1s |
| wire check | `docs/checks/speech-aware-evidence-acquisition/2026-09-09-e21-dr1-wire-check/` — **PASS**, all three cells, zero contacts, zero sockets |
| exposure row | `SAEA-E21-MF-DR1-PREP-V1` (model-free). **The three FLIGHT rows do not exist and must be registered, with `consumed = no`, before the first contact.** |

---

## 1. The measurement this family answers

OBS-E1 bought **+1.0487** points of corpus WER (CI90 `[+0.9253, +1.1745]`, 18.1 own-null half-widths)
and sold **2.0912** points of ConEC-mirror PERSON entity WER (`[−3.1701, −1.0978]`, 8.4 half-widths).
It was REJECTED as HARM. The model-free decomposition then named the sixty-one excess errors:

* **78.7 %** sit in units under **ten seconds**, which hold 23.3 % of the PERSON words;
* units of **sixty seconds or more were BETTER** in the cell than in the comparator, by seven errors;
* **93.4 %** of the harm is within three seconds of a unit boundary, and the comparator's own PERSON
  rate over those same words is flat — the words are not intrinsically harder;
* the cut goes through a multi-word name **once in 656**, so the damage is *beside* the name;
* **both edges** are damaged and the end only 1.2 times worse than the start;
* three quarters of the harm is **substitution**, not deletion.

A truncate-at-the-tail failure produces an end-side effect. A **missing-context** failure produces
both. There are exactly two ways to give a short unit back the conditioning its shortness removed:

* **give it more AUDIO** — a context margin around the turn. That is **OBS-E1b**, already prepared
  (`docs/readiness/2026-09-08-e21-obs-e1b-context-units-v1-preregistration.md`), and §9 says how this
  family relates to it;
* **give the LONG window the short unit's TEXT** — draft with the short speech, refresh with the long
  speech. That is **DR-1**, and it is what the owner asked for.

DR-1 is also the cheaper of the two to prove. It re-cuts no audio, so it needs no new stitch protocol
and no forced alignment; its regrouping is arithmetic on sealed bytes; and its floor is provable
model-free, on real sealed bytes, before any contact (§7).

## 2. The cell, as the four agents

Per the design note's §6 template (`docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md`).

| agent | what it does here | seam |
|---|---|---|
| **Planner** | meeting task → two observe passes composed rather than contrasted: the sealed speaker-turn units draft, the fixed 90-second window refreshes. Budget: exactly one core call per window; stop after it | the config fragments; no loop condition, deliberately — DR-1 is a **single** refresh, as the owner's words say |
| **Observer** | pass 1 = the sealed OBS-E1 speaker-turn units, **read, not re-flown**, regrouped onto the comparator's window grid by `saea-e21-unit-draft-majority-overlap-v1` and bound content-free. Pass 2 = the comparator's own fixed 90-second windows, byte-identical protocol, no VAD trim, no tail, no preprocessing | `core.predecessor_snapshot`; `reproduction.obs_loop`'s fixed tiling |
| **Solver** | the frozen core, once per window, hearing the whole 90 seconds and shown that window's draft as typed material | `reproduction.repair_loop`'s `window_hook`, frame `e21-draft-refresh-frame-v1` |
| **Reviewer** | **DR-1c and DR-1s**: `e21-entity-repair-substitutions-v1`, the substitution-only alignment rule — the one judge in the design note's inventory that is a delivery constraint, scoring and refusing an illegal edit and never proposing text. **DR-1f**: the Reviewer is switched OFF, and that is the factor | `core.repair_alignment`; the refusal table is the judge's verdict |

**Knowledge is absent by design.** The arm is `bare-core`, `evidence_source` is `none`, and the
payload carries exactly the comparator's D2-frozen field set. DR-1 asks what the *system's own
earlier observation* is worth, with no external knowledge in the request at all — which is also what
makes the KC-E1f cross-reading in §6.4 meaningful.

## 3. What is delivered, and what is stitched

**Pass 1 is not re-flown.** OBS-E1 already decoded all 5,122 units, and its bytes ARE the draft.
Re-flying it would double the contacts, spend a second 1.07 GPU-h, and — because greedy decoding on
llama-server is not bitwise reproducible across batch compositions — would produce a draft that is
*not* the arm this family is read against.

**The ownership rule, fixed model-free and quoted from the module.** A unit is owned by the sealed
90-second window it overlaps most; a tie goes to the earlier window; a window's draft is its owned
units' sealed texts joined by `reproduction.obs_loop`'s own stitch rule.

**The proof, on sealed bytes** (`.../2026-09-09-e21-dr1-unit-draft-stitch/`). Both sealed runs first
reproduce their own published counts and rebuild all 44 of their own sealed hypotheses byte for byte.
Then: all **5,122** units are owned exactly once; ownership is **non-decreasing in unit index**, so
the stitch cannot reorder a call's words; and concatenating the per-window drafts reproduces the
sealed OBS-E1 hypothesis of **44 of 44 calls, byte for byte** — asserted against `outputs.jsonl`
directly, not through the recovery, so the chain is checked end to end. Every drafted row carries the
comparator's own window id, index and bounds to 1e-9 s, because `RepairWindowHook` refuses a cut
window that disagrees with its predecessor by more than 1e-6 s.

**Two windows of the 1,593 own no unit** — `4361631#w0050` (1.429 s) and `4387865#w0025` (2.573 s),
both the last, remainder window of their call. The corpus loses nothing: the words spoken there are
inside the covering unit's text, which the preceding window delivers, and that is why the
byte-for-byte proof holds. Their draft is the empty string; **both** delivery rules refuse an empty
draft as `empty_predecessor` and deliver the empty string, so the two arms treat them identically.
**Three units of the 5,122 saturated** in OBS-E1 and contributed the empty string to their windows'
drafts; their 3,072 quarantined tokens are counted apart from the 442,270 that are actually in a
draft, so no prompt fit is inflated by a decode that produced nothing.

**Pass 2**, per window: the window's own 90 seconds of audio, the fragment's `task_instruction`, and
that window's draft inside the frozen frame at the END of the rendered instruction — exactly where
`obs_loop`'s own conditioned tail rides. It is model output, framed as model output, never a
reference transcript, and it lands verbatim in the sealed `MODEL_REQUEST` record. **The draft is
never interpolated into the instruction body** (the containment rule): the instruction a reader can
quote is the instruction that was sent, and the draft is material beside it.

The instruction is one string for all three cells, and its last three sentences are the sealed
comparator's whole instruction, **byte for byte** (asserted by the wire check):

> A draft transcript of this same audio window follows below. Listen to the audio and produce the
> final transcript of the window: keep the draft's words wherever the audio confirms them, and
> correct them wherever it does not. *Transcribe the speech verbatim exactly as spoken. Never insert,
> repeat, or add any word you do not clearly hear in the audio. Output only the transcript text.*

**"Only substitutions" is not in the instruction, and must not be.** An instruction is a request; the
harness is the enforcement (`core.repair_alignment`'s module docstring, and the design note's
Decision 11-C split). DR-1c and DR-1f send the *identical* request and differ only in what the
harness accepts back.

## 4. The three cells, and the one factor each moves

| | DR-1c | DR-1f | DR-1s |
|---|---|---|---|
| draft | stitched unit draft | stitched unit draft | **the comparator's own sealed hypothesis** |
| delivery | `e21-entity-repair-substitutions-v1` (4 / 0.60 / 0.10) | `e21-free-refresh-delivery-v1` | `e21-entity-repair-substitutions-v1` (4 / 0.60 / 0.10) |
| what it isolates | — (the reference cell) | **the delivery rule** | **the draft's source** |
| floor, if every answer is refused | the sealed OBS-E1 transcript | the sealed OBS-E1 transcript | the sealed comparator transcript |

**DR-1c vs DR-1f: the delivery rule, and nothing else.** The fragments carry the identical key set
and differ in exactly `response_postprocessor` and `response_postprocessor_params` — checked on the
composed documents by both the wire check and the prompt fit. The free rule keeps exactly two of the
bounded rule's four whole-response refusals (`empty_predecessor`, `empty_response`) precisely so that
an empty draft and a saturated decode are handled identically in both arms; what it drops
(`anchor_ratio_below_floor`, `substituted_fraction_above_ceiling`) IS the factor. A summary, a
translation or a runaway is *delivered* in DR-1f, and the corpus-WER and over-generation guards are
what catch it. That is the KC-E1 risk — a free whole-window rewrite cost **2,242** extra non-entity
deletions — measured rather than feared.

**DR-1c vs DR-1s: the draft's source.** The fragments differ in exactly `predecessor_snapshot`. The
frame's wording is deliberately neutral about where the draft came from — every clause is true of
both drafts — so the twin does not also change what the model was told. DR-1s asks the question that
would otherwise be unanswerable: **does a refresh help at all, without the short-unit draft?**

**Token matching is by MEASUREMENT, not assertion.** Over the 1,593 windows the stitched unit draft
runs 229 / 361 / 505 whitespace tokens (median / p95 / max) and 273 / 432 / 596 flight tokens; the
comparator's own hypothesis runs 280 / 344 / 445 flight tokens. Medians differ by 2.5 %; the unit
draft's tail is the longer one, because a window owning many short units accumulates a boundary's
worth of tokens each time. Both distributions are reported in every verdict table.

**The delivery parameters are KC-E1f's own committed values, unchanged**, and that is a decision with
a stated cost. On a median 229-word draft the bounded rule accepts at most about 23 substituted
tokens and refuses a wider rewrite whole. A refresh that needs more than that is refused and the
draft is delivered — which is a real limit on what DR-1c can buy, and is exactly what DR-1f bounds
from the other side. Moving those parameters would both tune a knob and add a second factor against
KC-E1f, so they do not move.

## 5. Roster, pairing, estimator — all unchanged

Not one of these moves from the comparator, OBS-E1, KC-E1f or the null replicate, and that is
deliberate: a cell whose estimator moved could not be read against them.

* **Roster**: all 44 `earnings21-original` discovery calls, split identity `fcc1b0bc…d69e`. No draw.
* **Pairing unit**: the fixed 90-second window, **1,593** of them. Every window is delivered by every
  arm, so the paired read is over the same 1,593 units the comparator, KC-E1, KC-E1f and the null
  replicate were read on.
* **Bootstrap cluster**: the call, **44**.
* **Estimator**: the pooled ratio through
  `analysis.paired.resampled_statistic(cluster_of=analysis.e21_window_pairing.call_of)`, seed
  **20260903**, **10,000** replicates, **CI90**, reported under **both weightings** (natural mixture
  and equal stratum).
* **Scoring**: one pass of `core.scoring_batch` over each complete manifest, five declared scorers,
  never sharded.

## 6. The decision rule, fixed before the flight

Signed so that a POSITIVE value means fewer errors (comparator − cell).

### 6.1 Primary

> **ADMITTED as an observe-plus-refresh module** iff, on the reported roster, the call-clustered CI90
> **lower bound** on the **corpus-WER reduction** against the sealed comparator is **> 0**, AND
> ConEC-mirror PERSON entity WER is **non-inferior** to the comparator at this carrier's own margin —
> `LB(ΔPERSON) >= −0.25009` — AND every gating guard in §6.3 holds.
>
> **ADMITTED AS AN IMPROVEMENT** if, in addition, `LB(ΔPERSON) > 0`.
>
> **NULL** if the corpus-WER lower bound includes 0 while every guard holds.
>
> **REJECTED** if the PERSON non-inferiority fails or any gating guard fails, with the failing half
> named and the per-class table published either way.

The margin **0.25009** is the half-width of `SAEA-E21-FULL44-NULL-REPLICATE-V1`'s own call-clustered
CI90 on ConEC PERSON entity WER, whose null interval is `[−0.24338, +0.25680]`. It is a number another
cell measured on this carrier under a null in which nothing was changed, and it predates this
contrast. **Reported beside the primary, not gating**: whether each effect's interval is disjoint from
its own null band, stated explicitly rather than left to a reader to divide.

**Why corpus WER is the primary here and PERSON is the non-inferiority half.** OBS-E1 won corpus WER
by 18.1 own-null half-widths and lost PERSON. This family exists to keep that gain without that loss,
so the thing it must demonstrate is the gain and the thing it must not pay is the loss. That is the
mirror image of KC-E1f's rule, and it is chosen because the *predecessor cell's* result chose it —
not because of anything DR-1 will produce.

### 6.2 The attribution leg

`LB(ΔPERSON)` and `LB(Δcorpus WER)` of **DR-1c against DR-1s**. **Gating for the CLAIM, not for the
admission**: if this leg's interval includes zero, DR-1c may still be ADMITTED on §6.1, and the
verdict may then say the refresh helped but **may not say the short-unit draft is why**.

### 6.3 Guards, all non-inferiority at this carrier's own measured margins

| # | guard | rule | margin | source |
|---|---|---|---:|---|
| 1 | delivery integrity (**DR-1c and DR-1s only**) | every window's delivered text equals its bound draft outside the accepted substitution spans, with the identical whitespace-token count; a construction check that **ABORTS the read** on failure | — | construction |
| 2 | window coverage | every one of the 1,593 windows is delivered exactly once; a construction check that **ABORTS the read** | — | construction |
| 3 | ConEC non-entity WER | `LB(Δnon-entity) >= −0.06475` | 0.06475 | null verdict §3 |
| 4 | numeric-value accuracy, call-pooled | `LB(Δnumeric) >= −0.15651` | 0.15651 | null verdict §3 |
| 5 | over-generation, insertions per 100 reference words | `UB(cell − comparator) <= +0.02218` | 0.022178 | KC-E1f v2 re-decision §4, computed from the null replicate's own per-window rows |
| 6 | negation-critical / semantic high impact | advisory, gates nothing | — | the null's own interval excludes zero, so the clause is unanswerable on this carrier (v2 §2.3) |

Guards 1 and 2 gate by construction; 3, 4 and 5 gate statistically; 6 does not gate.

**Guard 1 does not exist for DR-1f, and that is not an exemption.** A free delivery cannot satisfy a
token-count invariant, and pretending otherwise would be dishonest bookkeeping. DR-1f's deletions and
insertions ARE the measurement, and guards 3, 4 and 5 are what bound them. Its verdict must say
explicitly that the arm carried no delivery-integrity guarantee.

### 6.4 Secondary reads, reported and never gating

* **Against OBS-E1**: does the refresh recover the names the units lost? OBS-E1's own PERSON 24.58005
  and corpus WER 7.15078 are the reference. OBS-E1 is REJECTED and is quoted as a comparator, never as
  an admitted effect.
* **Against KC-E1f**: is a knowledge-free refresh competitive with the brief repair? KC-E1f took
  PERSON to **18.752** with the cap-12 ConEC brief; DR-1s is the same second pass over the same draft
  with the brief and the entity-repair instruction removed. KC-E1f's admission is **provisional with
  its replication UNMET**, so it is quoted as a comparator and **this family cannot discharge that
  replication** — a different mechanism is not a second pass of the same one.
* **The OBS-E1 harm strata, re-read on the delivered text**: unit duration class, distance to the
  nearest unit boundary, end-cut kind. This is the read that says *whether the refresh reached the
  stratum that carried the 61 excess errors*, and it is descriptive at every level below the top.

### 6.5 Core-pressure covariates, reported by the verdict

Not decision criteria. **Contacts**: one charged pass-2 contact per window, 1,593 per arm; pass 1
costs this family nothing because it is read, and OBS-E1's own sealed **1.0657 GPU-h** for those
5,122 units is stated here so a reader can price the episode end to end rather than only its second
half. **Tokens**: prompt and completion per contact and in total, against the comparator's
1,935,965 / 439,532 and KC-E1f's 3,550,695 / 434,219. **Delivery ledger**: windows refused by reason,
windows changed, accepted substitutions, substituted tokens and rejected opcodes by class — all four
classes at zero if that is what they are — for both rules, in one table. **Saturation**: pass-2
saturated windows per arm (the comparator sealed 0 of 1,593; OBS-E1 sealed 3 of 5,122), plus the two
empty-draft windows, reported as covariates and never as exclusions. **Delivered audio seconds** and
**the share of the final transcript the control plane delivered unchanged** (KC-E1f's own figure: 447
of 1,593 windows untouched, 82 refused).

## 7. What has been proved model-free, and what has not

`docs/checks/speech-aware-evidence-acquisition/2026-09-09-e21-dr1-wire-check/` — **RESULT PASS, zero
failures**, clean tree, `study_repo_dirt` empty. Zero contacts, zero sockets.

| half | what it proved |
|---|---|
| `config` | all three cells COMPOSE. DR-1c `929af786…` / `791e21d8…`, DR-1f `30ebd82c…` / `b4a4d4f6…`, DR-1s `61a8ac64…` / `17166454…`, all against split identity `fcc1b0bc…d69e`. DR-1c differs from DR-1f in exactly `response_postprocessor` and `response_postprocessor_params`, from DR-1s in exactly `predecessor_snapshot`, and from KC-E1f in exactly `arm`, `evidence_source`, `brief_max_entries_per_class`, `predecessor_snapshot`, `repair_frame` and `task_instruction`. The three cells share ONE `task_instruction` and it ends with the comparator's own, byte for byte |
| `request` | on 4 calls and 160 windows, every rendered instruction **equals** the fragment's instruction plus the frozen frame filled with that window's own draft; a fully refused pass 2 rebuilds **each arm's own floor byte for byte** — the sealed OBS-E1 hypothesis for the unit-draft cells, the sealed comparator's for the twin, 4 of 4 calls each; the two delivery rules **agree on every refusal**; every window is delivered exactly once |
| `delivery` | a labelled divergence probe: fed the comparator's own sealed hypothesis as a pretend response, the bounded rule refuses **14** of 160 windows (7 anchor floor, 7 substitution ceiling), changes 132 and accepts **654** substitutions, while the free rule would move **8,907** whitespace tokens. The bounded rule never moves a window's token count on that real text |
| `payload` | the shared `rails.core_client.payload_binding_stage` over the 44-row roster BINDS |

**The floor is the property worth naming twice, and it is not the same floor for every arm.** If the
core answered every window with nothing usable, DR-1c and DR-1f would deliver the sealed **OBS-E1**
transcript exactly, and DR-1s would deliver the sealed **comparator's**. So DR-1c's floor is a cell
that is REJECTED on PERSON and better on corpus WER, and DR-1s's floor is the comparator itself. A
reader must hold that asymmetry when reading the twin leg: the two arms do not start from the same
place, and §6.2 is a contrast of *movements*, not of endpoints.

**What is NOT proved, and is named rather than left to be discovered.**

1. **No contact has been made**, so nothing here says the core will use a draft well. It may copy the
   draft (delivering OBS-E1's PERSON harm intact), it may ignore it (delivering something near the
   comparator), or it may do something else. Which of those happens is the measurement.
2. **The bounded rule's ceiling may bite.** The probe's 14 refusals in 160 windows are against a text
   the core did not produce; a real refresh could refuse more often or less. The refusal count is a
   reported covariate and never a knob this cell tunes.
3. **The two empty-draft windows are handled identically by both rules but are not *nothing*.** DR-1f
   hears their 1.4 s and 2.6 s of audio with an empty draft and still delivers the empty string,
   because the rule refuses on the draft rather than on the response. That is a deliberate choice for
   one-factor cleanliness, it costs the corpus nothing (§3), and it is stated rather than smoothed.
4. **A projection is not a fit** (§8).

## 8. Budgets and the serving geometry

| | per cell | family of three | basis |
|---|---:|---:|---|
| core calls | 1,593 realized, **1,750** planned | **5,250** | the exact window count × 1.1 retry headroom; the comparator, KC-E1, KC-E1f and the null replicate each realized exactly 1,593 at this tiling |
| speech audio seconds | 141,348.532 realized, **150,000** planned | **450,000** | the comparator's own per-pass audio; the tiling is the comparator's and pass 1 is not re-flown |
| GPU hours | **1.1093** projected, **1.2** planned | **3.33** projected, **3.6** registered | KC-E1f's realized 1.1093 by the manifest's own nvidia-smi sampler for one pass of 1,593 windows at this tiling — with a cap-12 brief in the prompt that DR-1 does not carry, so the projection is if anything generous |
| pass 1 | **0**, stated | 0 | OBS-E1's sealed **1.0657 GPU-h** and 5,122 contacts were spent by that cell and are not re-charged here |
| paid API | 0 | **0** | in force |

**The geometry is projected, and a prompt fit decides it.** The projection is model-free and comes
from two measurements, not a characters-per-token guess: the comparator's own sealed per-window prompt
tokens (which already *are* speech plus template plus the comparator's instruction) and each binding's
sealed draft tokens.

| cell | draft flight tokens (max) | worst request | np6, slot 6,144 | np4, slot 9,216 |
|---|---:|---:|---:|---:|
| DR-1c / DR-1f | 596 | **2,954** | **2.080×** | 3.120× |
| DR-1s | 445 | **2,803** | **2.192×** | 3.288× |

Both clear the study's `slot_tokens >= 2 × worst_required` rule at np6, with little room, so the
threshold is written down before the fit measures it: **the declared geometry stops satisfying the
rule once the added envelope reaches 240 flight tokens**, 2.4× the 100 assumed for the one leading
instruction sentence plus the frame's fixed wording. If the SERVER fit lands past that, lever 1 of its
own pre-fixed procedure takes **np4**, which carries the same worst request at 3.120× and changes no
request byte. Lever 2 (lower the pass-2 completion ceiling below 1,024, against a largest sealed draft
of 596 tokens) is available and is an owner's option, never a silent one. **There is no third lever**:
KC-E1f's was the brief cap and DR-1 carries no brief.

The SERVER fit (`scripts/e21_dr1_prompt_fit.py`, run id `SAEA-E21-DR1-PROMPT-FIT-V1`) opens a session
and is therefore a model contact by this study's accounting: it is the flight agent's step, needs its
own registered exposure row, and must run before the first flight contact.

## 9. The relation to OBS-E1b, which stays prepared

OBS-E1b and DR-1 act on the **same diagnosis** by opposite means, and neither retires the other.

| | OBS-E1b | DR-1 |
|---|---|---|
| what the short unit gets back | **audio**: a 5.0 s margin per side, floored at 10 s and capped at 90 s | **text**: its own draft, read by a contact that hears the whole 90 s |
| contacts per pass | 5,122 | 1,593 |
| delivered cut | 191,314 s (+35 % over OBS-E1) | 141,346 s — the comparator's own |
| new stitch protocol | yes: `saea-obs-context-ownership-v1`, an overlap alignment that **can** drop a word (adversarial retention 97.110 %) | no: whole sealed unit texts are moved, and the regrouping provably drops none |
| its floor, model-free | not a floor: the stitch is lossy under an adversarial overlap | the sealed OBS-E1 transcript, byte for byte |
| what it cannot do | it cannot use the long window's own conditioning | it cannot change what the short unit heard |

**OBS-E1b stays prepared and unflown, and this document does not touch it.** Its preregistration, its
plan pins and its wire check stand. One experiment is in flight at a time; the owner's Decision 13-J
named DR-1, so DR-1 is the one prepared here. If DR-1 is admitted, whether OBS-E1b is still worth its
pass is an owner's call and not an analyst's — and the honest reason to keep it on the table is that
the two mechanisms could be complementary: DR-1 cannot repair what the short unit never heard, and a
margin is the only candidate measured to act on that.

## 10. Claim surface

Discovery data. No superiority claim, no generality claim, no Stage-3 claim, no
`paper-scale-confirmatory` profile, no Earnings-22 contact, no confirmatory read, no knob tuned on the
evaluation ten. n = **44 clusters**, below the program's `n >= 400` rule, so **no paper-facing
effectiveness claim is available to this family in either direction**; the interval and the direction
are the deliverable. The E5 evaluation half carries 342 paired windows, likewise below the rule, and
is reported apart and descriptively with no interval quoted.

**What each cell cannot conclude, listed so the verdict cannot forget.**

* **DR-1c alone** cannot separate "the short-unit draft helped" from "a second contact helped". That
  is §6.2's leg, and it needs DR-1s.
* **DR-1c** cannot say whether an unbounded refresh would have done better or worse. That is DR-1f.
* **DR-1f** carries no delivery-integrity guarantee and cannot claim one; its deletion and insertion
  counts are the measurement, not a defect report.
* **DR-1s** says nothing about the short-unit draft. It is the null of the source factor, and a
  positive DR-1s with a null DR-1c would mean the refresh, not the draft, is what works.
* **No cell** amends OBS-E1's REJECTED status, discharges KC-E1f's replication obligation, admits any
  module to a default plan, or says anything about Earnings-22 or about OBS-E1b.
* **The family as a whole** cannot separate the refresh from the transport unit as an observe mode: it
  keeps the comparator's transport throughout, and a cell that changed both would be two factors.

## 11. If it fails, what happens next — fixed in advance so it cannot be chosen afterwards

1. **DR-1c's corpus-WER lower bound includes zero, or PERSON fails non-inferiority.** Name it and
   stop. The successor is a preregistration, not an amendment; the first question it must answer is
   which stratum of §6.4's re-read the refresh failed to reach.
2. **DR-1c holds but DR-1s holds equally.** The gain is the second look, not the short-unit draft. The
   successor drops the unit draft entirely and the family's claim becomes a claim about a self-refresh
   — which is a smaller and different result, and must be reported as such.
3. **DR-1c is refused too often by the bounded rule** (a covariate, read against DR-1f's own delivery).
   The successor is DR-1f's result, not a re-parameterized DR-1c: the delivery parameters are
   KC-E1f's and moving them is a knob.
4. **A guard fails.** Name it and stop. The v1 KC-E1f verdict is the precedent: a guard failure is a
   result.

At most **one** recovery re-registration per flight, per the 2026-09-03 rules; a second failure stops
the flight and the fix is proven on a 4-row dry run first.

## 12. What this note does not authorize

It is not an owner GO to fly. Decision 13-J asked for the family and authorized the **model-free**
preparation; the three flight rows do not exist. No module enters any default plan on the strength of
this note, no geometry is decided by it, and the prompt fit that would decide one is itself a model
contact needing its own row.
