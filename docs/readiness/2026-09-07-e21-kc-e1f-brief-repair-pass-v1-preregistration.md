# KC-E1f — the Earnings-21 pre-meeting brief as a second-pass entity repair (v1)

**Status: PREREGISTERED, FLYABLE ON GO — with one precondition still OPEN.** Owner GO for this cell
is PENDING and nothing here is an authorization. The code, the sealed-predecessor binding, the
config fragments and the wire check are all done and committed (§8); the prompt fit is NOT, and its
model-free projection says the serving geometry this cell was written for **does not satisfy this
study's margin rule** (§7.1). That is a geometry decision, not an analyst's, so it is stated with
its numbers and left to the owner.

Named by the KC-E1 verdict's §12 (`docs/readiness/2026-09-07-e21-kc-e1-pre-meeting-brief-v1-
verdict.md`) and built as that section demands — "a new mechanism [that] needs its own
preregistration and its own owner GO", never off the back of that note.

Experiment fragment `configs/experiment/e21-kc-e1f-repair-44-v1.json`; arms
`configs/baseline/e21-kc-e1f-brief-repair.json` (KC-E1f) and
`configs/baseline/e21-ku-e1fc-placebo-repair.json` (KU-E1fc, the form twin); dataset fragment
`configs/dataset/earnings21-discovery-conec-names.json`. Program context:
`docs/readiness/2026-09-05-three-dimension-experiment-program.md` §4a / §4b.

---

## 1. The question, and the one factor

KC-E1's primary was **met on both legs and met comfortably** — PERSON entity WER 22.489 % → 18.341 %,
+4.148 pp with a call-clustered CI90 lower bound of +2.633 against the sealed comparator and +3.914
against its own token-matched twin — and the cell was **REJECTED**, because the brief bought its
names with ordinary words: **152 fewer PERSON substitutions, 2,242 more non-entity deletions**, and
both the corpus-WER and numeric-accuracy guards failed. The verdict's §6 localized the cost exactly:
83 % of the extra deletion mass is non-entity, and insertions actually *fell*. The model did not read
the brief aloud; it transcribed **less**.

So the question this cell asks is not whether the brief carries knowledge — KC-E1 already showed it
does, and showed the form twin makes things *worse*, so the content effect (+5.382) was larger than
the total effect. The question is whether that same knowledge can be spent **only on names**:

> Consumed as a second-pass entity repair over the comparator's own transcript, does the same capped
> brief recover PERSON entity WER **without** the transcript cost that rejected KC-E1?

**The one factor between the two cells is the brief's CONTENT**, exactly as in KC-E1: KU-E1fc sends
the same class labels, the same entry count and the same flight-tokenizer token count per line with
every entity string replaced by a position-chosen neutral placeholder. The two baseline fragments
differ in exactly two composed keys, `evidence_source` and the twin's own pad-plan byte pin.

**The factor against KC-E1 is the CONSUMPTION FORM at identical knowledge.** Both supply the same
cap-12 brief, built from the same two ConEC files by the same transform, with the same
`brief_max_entries_per_class` byte. They differ in whether the brief conditions the only decode or
edits a sealed one. That is a cross-cell reading, reported, never this cell's decision.

## 2. Pass 1 is not re-flown, and why that is the honest choice

The sealed comparator `SAEA-E21-FULL44-DIRECT-BASELINE-V2`
(attempt `attempt-20260904T233816Z-bcd338`) already decoded every one of the 1,593 windows. Its bytes
**are** pass 1.

Re-flying pass 1 would cost a second contact per window and a second pass of GPU hours, and — because
greedy decoding on llama-server is not bitwise reproducible across batch compositions (the KC-E1
verdict's §11 item 7 measured the build-and-audio-path noise at 0.05 corpus-WER points) — it would
produce a pass 1 that is **not the arm this cell is paired against**. Binding the sealed one makes the
comparison exact and makes the cell cost **one contact per window**.

**The binding is content-free.** `docs/receipts/e21-predecessor-full44-direct-baseline-v2.json`
(sha256 `26f1d9cc…a72a`) carries the artifact's path, size and sha256, the sealed
manifest/outputs/trace hashes, the counts, a chain hash over `(window_id, text_sha256)` and the
distributions — **not one hypothesis character**. The per-window hypotheses are model output and live
under `SPEECHRL_DATA_DIR` with the sealed outputs. This is the Earnings-shaped counterpart of
`rails.phase_material.sealed_states_from_manifest`, which is how KC-S1b conditions on the sealed
closed-list intent without re-flying it; one unit finer, because a SLURP sample is a row and an
Earnings sample is a 40–75 minute call whose sealed outputs row is a single stitched hypothesis.

**The recovery is proved, not assumed.** `analysis.e21_window_pairing.stitched_windows_from_trace`
recovers the spans and `assert_stitch_reproduces_outputs` refused to let a row be written until all
44 sealed hypotheses rebuilt **byte for byte**. Five identity anchors then had to agree with the
sealed run's own committed numbers: **1,593 windows / 44 calls / 0 saturated / 439,532 completion
tokens / 1,935,965 prompt tokens**. All five PASS. `core.predecessor_snapshot.
load_predecessor_binding` re-verifies the whole chain at flight time, in a fixed refusal order, before
a single window becomes readable.

## 3. Pass 2 — the only contact, and what it is allowed to change

Each window's single request carries, in this order: the two `[evidence …]` brief blocks (roster then
document, cap 12), the fragment's task instruction, and **that window's sealed pass-1 hypothesis**
inside the frozen frame `e21-entity-repair-frame-v1`, then the window's 90 seconds of audio. The
predecessor rides at the end of the rendered `task_instruction` — exactly where
`reproduction.obs_loop`'s own `OBS_TAIL_FRAME_V1` conditioned tail already rides — so **the arm's
D2-frozen payload field set is untouched and no new key reaches the wire**. It is model output,
labelled as model output, never a reference transcript, and it lands verbatim in the sealed
`MODEL_REQUEST` record.

### 3.1 The delivery rule, stated exactly

"Change only names" cannot be an instruction; an instruction is a request. The enforcement is
`core.repair_alignment`, registered as `e21-entity-repair-substitutions-v1` in the
`core.base.RESPONSE_POSTPROCESSORS` registry and named by both fragments, so the rule and its
parameters ride in the composed config hash.

1. Both texts are tokenized on whitespace runs (`\S+`); the pass-1 side keeps character offsets, so
   an untouched token is delivered as its **own original bytes**.
2. `difflib.SequenceMatcher(a=pass1_tokens, b=returned_tokens, autojunk=False)` produces the opcodes.
   `autojunk` is off because the heuristic it enables suppresses popular elements in long sequences,
   and a transcript's popular elements are the function words that anchor this alignment.
3. Disposition, and only one of these can change a byte:

   | opcode | disposition |
   |---|---|
   | `equal` | the pass-1 bytes are delivered verbatim |
   | `replace`, same token count on both sides and `<= 4` tokens | **ACCEPTED** as a substitution |
   | `replace`, unequal token counts | rejected — `unbalanced_replace` |
   | `replace`, same counts but `> 4` tokens | rejected — `oversized_replace` |
   | `insert` | rejected — the returned tokens are dropped |
   | `delete` | rejected — the pass-1 tokens are delivered verbatim |

   An unequal-length `replace` is rejected because it **is** an insertion or a deletion wearing a
   substitution's clothes; accepting it would move the token count and reopen the failure this cell
   exists to close.
4. Three whole-response **refusals**, checked after the opcodes and before any splice. A refusal
   delivers the pass-1 text byte for byte and names itself:
   * `empty_response` — the response is empty or all whitespace (this is also where a **saturated or
     skipped** pass-2 decode lands, because the base policy's quarantine hands the rule an empty
     string);
   * `anchor_ratio_below_floor` — the `equal` opcodes cover less than **0.60** of the pass-1 tokens;
     a response that summarized, translated, answered a different question or ran away has no anchor
     and its "substitutions" are alignment noise;
   * `substituted_fraction_above_ceiling` — the accepted substitutions would rewrite more than
     **0.10** of the pass-1 tokens; a wholesale rewrite that happens to preserve token counts is
     still a wholesale rewrite.
   A fourth reason, `empty_predecessor`, exists for a window the comparator itself quarantined; the
   comparator has **zero** such windows, so it cannot fire here.
5. Accepted substitutions are spliced into the pass-1 STRING by character offset, right to left, so
   every unsubstituted byte — punctuation, casing, spacing — survives exactly.

**The invariant, asserted in code on every outcome**: `len(delivered.split()) ==
len(predecessor.split())`. A violation raises rather than returning, because a delivered hypothesis
whose token count moved is exactly the defect this module exists to make impossible and it must never
be scored silently.

`tests/unit/test_e21_repair_alignment.py` proves the rule on synthetic pairs — an accepted one- and
two-token name repair spliced in place, a rejected insertion (including a brief read aloud at the
end), a rejected deletion (including KC-E1's own failure shape), a rejected unbalanced replace, a
rejected oversized span, all four refusals reachable by name, and the invariant over ten adversarial
responses.

### 3.2 The two parameters, and why they are not binding

`max_span_tokens = 4` and `max_substituted_fraction = 0.10` are ceilings on how much repair is
reachable, so a preregistration has to say whether they bind. **They do not.** The comparator's
per-window median is 238 whitespace tokens, so the 10 % ceiling admits about 23 substituted tokens per
window; the entire PERSON substitution mass the comparator carries is **573 tokens over 1,593
windows**, and KC-E1 repaired 152 of them. Four tokens is longer than any ConEC PERSON surface form in
the roster. The ceilings exist to catch a runaway, not to cap the mechanism.

## 4. The three arms

| arm | contacts per window | what it carries |
|---|---|---|
| **comparator** `SAEA-E21-FULL44-DIRECT-BASELINE-V2` (sealed) | 1 (pass 1 only) | bare core, 62-token envelope |
| **KC-E1f** | 1 pass-2 contact | audio + the sealed pass-1 hypothesis + the **real** cap-12 brief |
| **KU-E1fc** (form twin) | 1 pass-2 contact | audio + the same sealed pass-1 hypothesis + the **token-matched placebo** brief |

**The comparator is also the equal-contact control on the delivery, and the twin is the
equal-contact control on the content.** The comparator sends no pass-2 contact at all, so the
comparator contrast moves two things — that a second contact exists, and that it carries the brief —
and is reported as repair-pass-plus-brief, never as the content effect. The twin pays the identical
contact with the identical instruction, the identical frame and the identical predecessor, so
KC-E1f − KU-E1fc **is** the content effect, exactly as in KC-E1.

The twin replays the same hash-pinned pad plan KU-E1c flew
(`configs/knowledge/e21-brief-placebo-v2/pad-plan-v1.json`, sha256 `e3b494d0…d49c`), so its brief is
token-equal to the arm's line by line and call by call on the flight tokenizer, with the same constant
**+7-token** residual from the two `[evidence <id>] ` headers that KU-E1c carried. That residual is a
property of the evidence-id names and not of the brief; a verdict must say so rather than claim a
perfect match.

## 5. Pairing, metrics, and the decision rule

**The paired unit is the fixed 90-second window (1,593). The bootstrap cluster is the call (44). The
call-clustered interval governs; the window-level interval is reported beside it, explicitly labelled
the optimistic bound.** Unchanged from the KC-E1 preregistration's §3 and the owner's 2026-09-06
ruling, on the same instrument (`analysis.e21_window_pairing`, exposure row
`SAEA-E21-MF-WINDOW-PAIRING-V1`) with the 2026-09-07 saturation fix.

Estimator: the **pooled ratio**, `sum(errors) / sum(reference words)`, through
`analysis.paired.resampled_statistic(cluster_of=analysis.e21_window_pairing.call_of)` at seed
**20260903**, **10,000** replicates, **CI90** — the same draws
`analysis.paired.paired_contrast` uses for the descriptive saves / harms / ties and the exact sign
test. Manifest scorers, declared in each flight's own manifest and run once per complete manifest
through `core.scoring_batch`, never sharded: `asr-wer-whisper`, `conec-entity-wer-official`,
`numeric-value-accuracy-v1`, `semantic-high-impact-error-rate-v1`, `cost`.

**Primary**: ConEC-mirror **PERSON** entity WER, then all eight published classes with their
reference-word counts, beside ConEC Table 2 rows 1 (biasing floor), 8 (Whisper large, no biasing) and
5 (the post-hoc oracle 13.0), and beside KC-E1's own per-class table.

> **ADMITTED** iff, on the reported roster, the **call-clustered CI90 lower bound** on the PERSON
> entity-WER **reduction** — pooled `(S + D) / tagged reference words`, comparator minus KC-E1f, so a
> positive value means fewer errors — is **> 0 against the sealed comparator** AND **> 0 against
> KU-E1fc**, and every guard below holds.
>
> **NULL** if either lower bound includes 0. A NULL with a positive point estimate against the twin
> and a negative one against the comparator is reported as "the form carried it", and the next cell
> is a supply-form question, not a content one.
>
> **HARMFUL** if any guard fails, with the failing guard named and the per-class table published
> either way.

**Guards**, in the same shape KC-E1 was judged by, plus the one this mechanism adds:

| guard | test | unit |
|---|---|---|
| **delivery integrity** | for every window, the delivered raw text equals the sealed predecessor outside the accepted substitution spans and carries the identical whitespace-token count — a **construction check**, verified from the sealed trace, that **aborts the read** rather than producing a number | window |
| corpus WER non-inferiority | call-clustered CI90 **upper** bound on (KC-E1f − comparator) pooled corpus WER **<= 0** | window rows, call-clustered |
| numeric-value accuracy not worse | CI90 lower bound on (KC-E1f − comparator) accuracy **>= 0**, on the **call-pooled** figure | call |
| over-generation not worse | insertions per reference word against the comparator's 10,700 / 359,765 | window rows, call-clustered |
| negation-critical rate not worse | point estimate with the taxonomy id; **advisory only** | window rows, reported |

**The numeric guard stays call-pooled** for the reason KC-E1's §5 gives: a bag match inside one window
is strictly stricter than one across the call, and the window rows measured that shortfall on the
comparator at 73 of 8,832 matched values.

### 5.1 What the construction guarantee does and does not survive normalization

The invariant is exact in **raw whitespace-token space**: the delivered hypothesis differs from the
comparator's only inside accepted substitution spans, with identical token counts. It is **not**
automatically exact after the Whisper normalizer, which is not a per-token map — a substituted surface
form can normalize to a different number of words (`1,000` → `1000`, `Mr.` → `mister`). So the
delivered hypothesis's *normalized* length can move, **but only by the normalization delta of the
substituted spans**, and nowhere else.

This is stated rather than assumed away, and it is reported rather than argued: the verdict publishes
the delivered-vs-comparator operation table (substitutions / deletions / insertions against the
comparator's 13,098 / 5,701 / 10,700) and, for every window whose normalized hypothesis length moved,
the substitution that caused it. **A deletion or insertion delta that cannot be attributed to a
substituted span is a defect report, not a result**, and aborts the read.

### 5.2 Covariates and strata

* **Pass-2 saturation** is a named covariate. `obs_repair_pass2_saturated` is recorded per window;
  such a window is a refusal that delivers pass 1, so it can never contribute an empty span the way
  KC-E1's two saturated windows did. The count per arm is published, and the sensitivity dropping the
  affected **calls** from all three arms is reported beside the primary, exactly as the KC-E1 verdict
  reported both saturation exclusions.
* **The repair ledger** is published whatever the outcome: windows refused by reason (all four
  reasons, even at zero), windows changed, accepted substitutions, substituted tokens, and rejected
  opcodes by class (all four classes, even at zero).
* Strata, all at the window unit and all **reporting dimensions, never knobs**: diarized speaker count
  and dominant-speaker class if `saea-diarization-v1` exists at read time (it does not block this
  cell), sector (9 levels), sample rate (5 levels), and the roster half (`kb-construction` 34 /
  `r4-e21-sub10` 10). Both natural-mixture and equal-stratum weighting.

### 5.3 What success would look like, as arithmetic and not as a prediction

The comparator's PERSON line is `S 573 / D 83` over 2,917 tagged reference words. **KC-E1f cannot
touch the 83 deletions** (§9 item 1), so its reachable floor is `83 / 2917 = 2.846 %` and every point
it wins must come out of the 573 substitutions. For scale, if it repaired the same 152 PERSON
substitutions KC-E1 did, the pooled line would read `(421 + 83) / 2917 = 17.278 %` — a reduction of
**+5.211 pp** against the comparator, larger than KC-E1's own +4.148, with the transcript untouched.
That is an illustration of the mechanism's arithmetic, published before any result so it cannot be
retrofitted, and it is **not** a prediction: nothing here says the repair pass will find the same
substitutions, and it may find none.

## 6. Budget

| | value | basis |
|---|---:|---|
| planned model calls | **3,500** | 1,593 windows + 157 retry headroom = 1,750 per cell × 2. The comparator and KC-E1 each realized exactly 1,593 at this tiling; pass 1 is read, not flown |
| planned speech audio seconds | **300,000** | 141,348.532 per pass × 2 = 282,697, rounded up. Same audio per pass as KC-E1 — the tiling is identical |
| planned GPU hours | **2.4** | KC-E1 realized 0.9948 GPU-h for one pass of 1,593 windows at this geometry with the cap-12 brief already in the prompt. KC-E1f adds the pass-1 text (a measured 3 / 280 / 445 flight tokens per window) to the same prefill and decodes a re-emission rather than a fresh transcript. 0.9948 × 1.2 = 1.194 per cell, rounded to 1.2 |
| paid API spend | **0** | unchanged and still in force |

Budgets are **run-cumulative across every attempt** of the run id. Re-measured on the preflight; the
flight **stops and reports** if the measured rate projects past 2.4 GPU-h. One experiment in flight; at
most one recovery re-registration, and a second failure stops the flight with the fix proven on a
4-row dry run first.

## 7. Preconditions

### 7.1 Prompt fit — **OPEN, and the projection says the geometry does not admit this cell**

`scripts/e21_kc_e1f_prompt_fit.py` is written and committed; its **server mode has not been run**,
because opening a session is a model contact by this study's accounting and belongs to the flight
agent with its own registered exposure row. What has been run is its **model-free** `--projection-only`
mode (receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-e21-kc-e1f-repair-44-v1/prompt-fit/
projection.json`, zero contacts of every kind), which combines two measurements rather than guessing:
KC-E1's own fit (fixed envelope overhead **179** tokens, per-call cap-12 briefs, worst 855-token text)
and the sealed pass-1 completion tokens per window (**3 / 280 / 445**, min / median / max, counted by
the flight server itself).

**At the committed cap 12 and the declared 6,144-token slot the projected worst request is 3,483
tokens: it fits STRICTLY and FAILS the study's `slot_tokens >= 2 × worst_required` rule at a margin
factor of 1.764.** (`4360366#w0036`; frame allowance 120 tokens — the frame's own flight cost is
unmeasured, so the receipt carries the whole sensitivity grid, 1.827 at frame 0 down to 1.744 at frame
160. No allowance rescues it.)

**Sweeping the cap does not rescue it either.** Not one value on KC-E1's own grid satisfies the rule at
this slot — cap 1 still reads 1.923 — because what the slot cannot afford is the **pass-1 hypothesis**,
not the brief.

The decision procedure is fixed in the script's docstring **before** the measurement, so a chosen
geometry can never be reverse-engineered from a result. In order:

| lever | at cap 12, frame 120 | margin factor | admits the cell? |
|---|---|---:|---|
| **1. widen the slot** — `-np 3`, 12,288 tokens | worst 3,483 | **3.528** | yes |
| **1. widen the slot** — `-np 4`, 9,216 tokens | worst 3,483 | **2.646** | yes |
| (`-np 5` is illegal here: 36,864 does not divide into a 512-multiple slot) | — | — | — |
| declared `-np 6`, 6,144 tokens | worst 3,483 | 1.764 | **no** |
| **2. lower the pass-2 completion ceiling** at `-np 6` — `max_tokens` 576 | worst 3,035 | **2.024** | yes |
| **3. sweep the cap** at `-np 6` | best is cap 1 | 1.923 | **no** |

Lever 1 is first because widening the slot changes **no byte of any request** — only how many share
the 36,864-token context — so it is a serving decision rather than a protocol one, and `-np 4` gives
back a comfortable 2.646 while giving up the least parallelism. Lever 2 is defensible on its own terms
(a pass-2 answer re-emits a text whose sealed maximum is 445 tokens, and the delivery rule refuses
anything much longer regardless) but it changes `decoding_params` and therefore the arm, so **it is an
option the owner takes and never a silent one**. Lever 3 is dominated and is reported only because
KC-E1's fit swept it.

**Nothing here chooses.** This document does not create a new model fragment and does not overrule the
`q4km-e21-buf90-mmproj-gpu-04ccc72a-np6` geometry the cell was scoped to. It states the frontier; the
owner picks, the fit certifies the pick, and the flight begins after that.

The cap-sweep rows for caps other than 12 use KC-E1's per-cap **worst** brief rather than a per-call
one, so those rows are an upper bound and strictly conservative — which is why the sweep is not
monotone at 10 and 8. The committed row is exact per call.

### 7.2 Wire check — **DONE and PASS**

Receipt `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e21-kc-e1f-repair-44-v1/
wire-check/wire-check.json`, run id `SAEA-E21-KC-E1F-WIRE-CHECK-V1`, study commit `66c8727d`, clean
tree, both cells, 61 contacts each over the four shortest kb-construction calls (17 / 13 / 15 / 16
windows), attempts FINALIZED, bundles verified, all five declared scorers producing aggregates, zero
failures.

**Zero model contacts, proved twice per cell from the sealed artifacts rather than the process
table.** KC-E1's own wire check *refused* to run beside a resident `llama-server`; that guard predates
the owner's 2026-09-07 always-on serving ruling, under which the core stays resident per geometry and
agents attach rather than spawn, so it is replaced by two direct proofs: the sealed session receipt is
the dry-run placeholder (`dry-run/no-real-binary`, pid 1, port 1, written only on the `--dry-run`
path), and every one of the 61 sealed per-slice `MODEL_RESPONSE` texts is
`core.driver.smoke._dry_run_transport`'s canned string. The resident session (pid 741, the `-np 6`
featcache geometry) is recorded in the receipt as context; nothing spoke to it.

Every repair property holds on both cells:

* the rendered `task_instruction` **equals** the fragment's instruction plus the frozen frame filled
  with that window's sealed hypothesis — one equality pinning the frame, the join and the
  window-to-predecessor mapping;
* every window records a delivery and a complete ledger, all four rejection classes present;
* **the delivered token count equals the predecessor's on every window**, on real sealed bytes;
* the dry-run transport's canned sentence is refused by the anchor floor on **61 of 61** windows, so
  every delivered span is its sealed predecessor byte for byte and **every stitched outputs row equals
  the comparator's own sealed hypothesis for that call**. A useless pass-2 answer costs nothing,
  measured rather than argued.

The one factor survives to the wire: same policy, same task instruction, same repair frame, same
predecessor binding, same contact count, same windows per call; different `evidence_source`, different
composed hash.

**One pre-existing condition, surfaced rather than swallowed**: `fixed-legal-context` predates the
2026-08-15 legality doctrine's either-field rule, so every run of it — these dry runs and the flight
alike — records provenance tier `UNVERIFIED` with a GRANDFATHERED declaration warning. That is a
property of the arm, carried so the flight is not surprised by it.

### 7.3 The payload-binding stage — **PENDING a merge, and named rather than skipped**

The brief for this work asks the wire check's request half to be run *through the payload-binding
stage* if that stage is on this branch. **It is not**: it lives on `wt/wirepay`. What ran here is the
existing request half — the payload key set against the arm's D2-frozen allowlist, the two evidence
items in roster-then-document order, the provenance relpaths, the per-half re-hash at cap 12, the OBS
tiling against the roster receipt's own window counts, the stitch/contact id agreement and the COST
record count — plus the five repair properties above. **The binding stage is pending that merge** and
should be re-run over this cell once `wt/wirepay` lands.

### 7.4 What is already closed, inherited

`e21_participant_names` in D1 (the additive, hash-pinned evidence supplement
`docs/receipts/artifacts/d1-e21-participant-names.json`, sha256 `313da4c4…fd83`) is closed and this
cell composes the same dataset fragment that pins it. The token-matched twin
(`SAEA-E21-KU-E1C-TOKEN-MATCH-V1`) is closed and this cell replays the same pad plan.

## 8. The flight agent's checklist, in order

1. **Owner GO for this cell**, and a geometry decision on §7.1. Without one, nothing below runs.
2. **Prompt fit** — `python scripts/e21_kc_e1f_prompt_fit.py` in its default (server) mode, on the
   chosen geometry, on a clean committed tree. It renders **every one of the 1,593 windows per cell**
   through the real transport with the real evidence and the real predecessor text, because this
   cell's envelope varies within a call by construction. Register its own exposure row
   (`SAEA-E21-KC-E1F-PROMPT-FIT-V1`) before it opens a session.
3. **Re-run the wire check** if the geometry moved, and re-run it through the payload-binding stage
   once `wt/wirepay` merges (§7.3).
4. **Register the exposure row** `SAEA-E21-KC-E1F-REPAIR-44-V1` before the first contact — split
   identity `fcc1b0bc…d69e`, both cells, the §6 budget, the inherited exposure of these 44 calls — and
   **commit it** before takeoff.
5. **Fly both cells** under one build, one serving geometry, one audio path. One experiment in flight.
6. **Score** each complete manifest once through `core.scoring_batch`, never sharded, under the four
   metrics plus cost. Then run `scripts/e21_window_pairing_read.py` on each cell's sealed outputs and
   trace — the recovery already prefers each window's `obs_delivered_text` — and **refuse to proceed
   unless the re-aggregation check passes**. Add each cell's sealed profile to that script's
   `SEALED_PROFILES` before running it, as every prior arm did.
7. **Run the delivery-integrity check first** (§5 guard 1, §5.1). It aborts the read; it is not a
   number.
8. **Verdict** against §5: the pooled call-clustered CI90 as the decision interval, the window-level
   CI90 beside it labelled optimistic, saves / harms / ties and the sign test at n = 1,593, the
   per-class table with reference-word counts, the repair ledger, the delivered-vs-comparator
   operation table, the saturation covariate with its call-level sensitivity, and every stratum of
   §5.2 under both weightings, on all 44 and on both halves of the E5 split.

**Exposure rows this cell's preparation produced or needs.** The model-free work already done —
the predecessor snapshot (`SAEA-E21-MF-PREDECESSOR-SNAPSHOT-V1`), the fit projection
(`SAEA-E21-MF-KC-E1F-FIT-PROJECTION-V1`) and the wire check (`SAEA-E21-KC-E1F-WIRE-CHECK-V1`) — is
recorded in the receipts named above but **is not yet written into `docs/exposure-ledger.md`**: that
file is contended by a flight in progress on another checkout and this branch does not edit it. The
coordinator lands those three rows on merge. Every one of them is `model-free-check` with zero model,
GPU, server, tokenizer, tool, embedder, network and paid-API contacts.

## 9. What this cell cannot conclude

1. **It cannot repair a deletion, by construction — so the comparator's PERSON deletions stay.**
   The delivery rule admits substitutions only, so the comparator's `D 83` PERSON deletions (and its
   5,701 corpus deletions) are inherited unchanged. Its reachable PERSON floor is therefore
   `83 / 2917 = 2.846 %`, not zero, and a word pass 1 never transcribed can never be recovered here.
   That is the price of the guarantee, and it is the whole trade this cell makes against KC-E1.
2. **It cannot say the brief is better consumed this way in general.** One carrier, one frozen core at
   Q4_K_M on build `04ccc72a`, one 90-second OBS tiling, greedy, 44 discovery calls. No superiority,
   no generality, no Stage-3 claim; `paper-scale-confirmatory` is neither available to this repository
   nor requested.
3. **No evaluation claim.** 34 of the 44 calls are the kb-construction half; the evaluation ten carry
   342 paired windows, below the program's `n >= 400` rule, and are reported apart and descriptively.
4. **It cannot separate the roster half of the brief from the candidate half.** Both are supplied
   together in every window; the per-class table is a class split, not an evidence-source split.
5. **It cannot say WHY a substitution was made or refused.** The ledger counts refusals by reason and
   rejections by class; no instrument here reads the model's reason for proposing an edit.
6. **It cannot attribute a gain to the audio versus the brief.** Pass 2 sees both. A brief-only
   variant (repair with no audio) would separate them and is a different cell, not a variant of this
   one.
7. **A small share of every difference is decode noise.** Greedy decoding on llama-server is not
   bitwise reproducible across batch compositions, and the two arms fly as two separate passes; the
   sealed verdict's own build-and-audio-path noise on corpus WER was 0.05 points. The delivery rule
   damps this — a noisy pass-2 answer is refused, not delivered — but it does not remove it.
8. **`fixed-legal-context` records provenance tier `UNVERIFIED`** with a GRANDFATHERED declaration
   warning (§7.2). A property of the arm, carried rather than discovered.
9. **Nothing about the whole brief.** Cap 12 is what KC-E1 flew and what this cell reuses so the
   knowledge is identical; §7.1 shows the slot cannot afford more here even in principle.

## 10. What this document is not

It is not an authorization to fly. The mechanism is built, the binding is verified, the fragments
compose, the wire check passes and the delivery guarantee is measured on the real rail — but the
owner's GO for this cell is a separate act, the geometry question of §7.1 is open and belongs to the
owner, and the prompt fit that would certify whatever geometry is chosen has not been run. What this
document fixes is the measurement: the unit, the estimator, the delivery rule and its parameters, the
strata, the guards, the failure modes and the illustrative arithmetic were all chosen before any
result existed.
