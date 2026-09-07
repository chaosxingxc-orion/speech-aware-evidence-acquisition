# KC-E1 — the Earnings-21 pre-meeting brief, whole prompt (v2)

**Supersedes `docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v1-preregistration.md`.** That
draft's §1, §2, §5 and §9 stand unchanged and are not restated here except where a number moves; this
document replaces its §3 (pairing), §4 (power), §7 (preconditions) and §8 (checklist), which is what
the owner's 2026-09-06 rulings and the three model-free rows landed since have changed.

**Status: PREREGISTERED, NOT AUTHORIZED TO FLY.** Both preconditions of v1 are now closed and the
wire check is done; §7 and §8 say what was measured. The cell still needs its own exposure row and
the owner's GO, and nothing here is an authorization.

Experiment fragment `configs/experiment/e21-kc-e1-brief-44-v1.json`; arms
`configs/baseline/e21-kc-e1-brief-whole-prompt.json` (KC-E1) and
`configs/baseline/e21-ku-e1c-brief-placebo.json` (KU-E1c, the form twin); dataset fragment
`configs/dataset/earnings21-discovery-conec-names.json`. Program context:
`docs/readiness/2026-09-05-three-dimension-experiment-program.md` §4a / §4b.

---

## 1. What did not change

The question, the arms, the one factor and the claim surface are v1's, verbatim in intent:

* the cell asks whether supplying the call's **own pre-meeting brief** closes part of the PERSON
  entity gap without costing corpus WER;
* **the one factor is the brief's CONTENT**, isolated by the form twin KU-E1c — same class labels,
  same entry count, every entity token replaced by a position-chosen neutral placeholder, and — since
  2026-09-07 — the same **flight-token** count per line rather than the same whitespace count (§5,
  "form twin token-matched on the flight tokenizer"). The two fragments differ in exactly two keys,
  `evidence_source` and `evidence_pad_plan`, the byte pin of the twin's own pad plan; that pin names
  no call content and changes nothing the arm renders;
* the contrast against the sealed comparator moves the evidence **and** the task instruction, is
  reported, and is never quoted as the content effect;
* the brief is built from two ConEC files per call and nothing else — no reference transcript, no
  timestamps, no `wer_tags`, no bias list — asserted by
  `tests/unit/test_class_lists.py::test_the_renderer_opens_no_reference_path`;
* the roster-line versus candidate-line split of v1 §2 is reported apart, because a gain carried by
  ConEC's labelled roster is a different finding from one carried by a cue-scanned keyword dump;
* discovery data only. No superiority, generality or Stage-3 claim; no knob tuned on the evaluation
  ten; no Earnings-22 contact; `paper-scale-confirmatory` is not available to this repository and is
  not requested.

## 2. The comparator, by name

`SAEA-E21-MF-AGENTIC-METRIC-BASELINE-V1` and `SAEA-E21-MF-SEMANTIC-IMPACT-BASELINE-V1`, on the sealed
`SAEA-E21-FULL44-DIRECT-BASELINE-V2` (attempt `attempt-20260904T233816Z-bcd338`).

| | all 44 | evaluation 10 |
|---|---:|---:|
| corpus WER % (`asr-wer-whisper`) | 8.200 | 7.185 |
| ConEC-mirror PERSON / ORG entity WER % | 22.5 / 17.2 | in `verdict/result-summary.json` |
| numeric-value accuracy % | 90.73 | 92.43 |
| negation-critical error rate % | 0.0278 | 0.0185 |

Pairing rules from `docs/readiness/2026-09-06-earnings-agentic-metric-baseline-v1.md` §7 hold: same
roster, same scorers, same `core.scoring_batch` path, and the headline for a mechanism is the entity
and numeric line, not corpus WER.

## 3. The pairing unit — the owner's 2026-09-06 ruling, and exactly what it buys

**The paired unit is the fixed 90-second window (1,593 of them). The bootstrap cluster is the call
(44 of them). The call-clustered interval governs; the window-level interval is reported beside it,
explicitly labelled as the optimistic bound.**

v1 §4 proposed this and left it to the owner. It is now ruled, and the instrument is built and
proven: `analysis/e21_window_pairing.py`, exposure row `SAEA-E21-MF-WINDOW-PAIRING-V1`, receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-window-pairing/`. Summing the 1,593
per-window rows reproduces the sealed corpus numbers **exactly** — corpus WER 8.200 %,
S 13,098 / D 5,701 / I 10,700 over 359,765 reference words, all eight ConEC classes with their
reference-word counts, non-entity 4.730, 1,479 unlabelled, 100 / 56 negation-critical. The
decomposition is therefore lossless, not approximate.

**What the window unit buys, stated so no verdict oversells it.** For a POOLED statistic with the
call as the cluster, resampling calls and pooling over their windows is arithmetically identical to
resampling calls and pooling over their totals: **the window unit changes no digit of the
call-clustered interval.** It buys exactly three things, and they are worth having:

1. the **window-level interval** as an explicitly labelled optimistic bound — 1,593 units treated as
   independent, which they are not;
2. a paired **saves / harms / ties** count and exact sign test at n = 1,593 rather than 44;
3. **per-window strata**, including the speaker strata of §4, which do not exist at any coarser unit.

**The estimator is POOLED, not a mean of per-window rates.** Corpus WER and ConEC entity WER are
`sum(errors) / sum(reference words)`; averaging per-window rates would let an 8-second tail window
weigh as much as a dense 90-second one. `analysis.paired.resampled_statistic` runs the pooled ratio
through the SAME cluster resampling `paired_contrast` uses — seed **20260903**, **10,000**
replicates, **CI90** — so the two estimators see identical draws.
`paired_contrast(..., cluster_of=analysis.e21_window_pairing.call_of)` supplies the descriptive
saves / harms / ties and the per-stratum table beside it.

**The `n >= 400` rule.** The program requires 400 paired units for an effectiveness claim. This cell
has 1,593 paired units and 44 clusters, and the honest interval is the 44-cluster one. That is
stated, not finessed: the rule is met at the unit the model contacts happen at, and the interval is
computed at the unit the independence claim survives at.

## 4. Strata — the speaker dimension, and what happens if it is not there yet

Reported strata, all at the window unit:

| stratum | source |
|---|---|
| **diarized speaker count** (`speakers=0/1/2/>=3`) | `saea-diarization-v1`, `reproduction.diarization` |
| **dominant-speaker class** (`dominated` / `shared`, 0.60 threshold) | the same artifact |
| sector, sample rate | the full-44 roster receipt, under natural-mixture AND equal-stratum weighting |
| roster half (`kb-construction` 34 / `r4-e21-sub10` 10) | reporting split; an evaluation claim quotes the ten's column only |

The speaker strata come from the pass pre-registered as `SAEA-E21-TOOL-DIARIZATION-V1`
(`docs/readiness/2026-09-06-e21-diarization-obs-v1-preregistration.md`), which has **not been run**.

**KC-E1 does not block on it.** If the artifact exists at flight time, the speaker strata are
attached at read time. **If it does not, the cell still flies** and the speaker strata are added
afterwards, from the sealed OBS artifact, over the same sealed window rows — the window ids are
stable (`<sample_id>#w<index>`, minted by one function and used by both modules) and the per-window
metric rows are already computed. This is not a loophole: **a stratum is a REPORTING dimension, never
a knob.** Adding one after the fact changes no cell, no arm, no metric and no decision rule, and the
decision rule below never conditions on a stratum.

The diarizer's 4-speaker design bound is narrower than an earnings-call roster, so `speakers>=3`
saturates and the dominance stratum is the primary one, with the count stratum reported beside it.
No diarization error rate is claimed.

## 5. Metrics and the decision rule

Manifest scorers, declared in the flight's own manifest: `asr-wer-whisper`,
`conec-entity-wer-official`, `numeric-value-accuracy-v1`, `semantic-high-impact-error-rate-v1`,
`cost`. Scored once per complete manifest through `core.scoring_batch`, never sharded; the per-window
decomposition is then computed from the sealed outputs and trace by
`scripts/e21_window_pairing_read.py`, never by an out-of-band scorer read.

**Primary**: ConEC-mirror **PERSON** entity WER, then all eight published classes with their
reference-word counts, beside ConEC Table 2 rows 1 (biasing floor), 8 (Whisper large, no biasing) and
5 (the post-hoc oracle ceiling of 13.0).

**Decision** — unchanged from v1 in substance, restated at the ruled unit:

> **ADMITTED** iff, on the reported roster, the **call-clustered CI90 lower bound** on the PERSON
> entity-WER **reduction** — pooled `(S + D) / tagged reference words`, comparator minus KC-E1, so a
> positive value means fewer errors — is **> 0 against the sealed comparator** AND **> 0 against
> KU-E1c**, and every guard below holds.
>
> **NULL** if either lower bound includes 0. A NULL with a positive point estimate against the twin
> and a negative one against the comparator is reported as "the form carried it", and the next cell
> is a supply-form question, not a content one.
>
> **HARMFUL** if any guard fails, with the failing guard named and the per-class table published
> either way.

**Guards**:

| guard | test | unit |
|---|---|---|
| corpus WER non-inferiority | call-clustered CI90 **upper** bound on (KC-E1 − comparator) pooled corpus WER **<= 0** | window rows, call-clustered |
| numeric-value accuracy not worse | CI90 lower bound on (KC-E1 − comparator) accuracy **>= 0**, computed on the **call-pooled** figure | call |
| negation-critical rate not worse | point estimate with the taxonomy id; **advisory only** — 14 HIGH reference words on the evaluation ten cannot gate anything | window rows, reported |
| over-generation not worse | insertions per reference word against the comparator's 10,700 / 359,765; a brief that gets read aloud shows up here first | window rows, call-clustered |

**Why the numeric guard is computed at call level, and it is not a dodge.** `numeric-value-accuracy-v1`
bag-matches a call's reference numeric values against the call's hypothesis values, and a bag match
inside one window is strictly stricter than one across the call: a value spoken in window 3 and
transcribed into window 4 matches at call level and not at window level. The window rows measured
that shortfall on the comparator — **73 of 8,832 matched values (0.827 %), across 27 of the 44
calls** — so the window-pooled accuracy reads 89.984 % against the sealed 90.734 %. The guard
therefore stays on the call-pooled figure, where the comparator's own published 90.73 lives, and the
window-level numeric rows are reported as a diagnostic only. `expected_numeric_words` partitions
exactly (9,734) either way.

**Reported whatever the outcome**: the per-class table with reference-word counts; all 44 / 34 / 10
apart; the roster-line versus candidate-line split; the brief's flight-tokenizer token distribution;
every stratum table of §4 under both weightings; throughput and token totals against the comparator's
1,935,965 prompt / 439,532 completion; both intervals of §3 with the optimistic one labelled.

**2026-09-07 — form twin token-matched on the flight tokenizer.** §7 item 2 recorded that KU-E1c was
a WHITESPACE twin and not a token twin: at cap 12 the placebo rendered 42 to 256 flight tokens
shorter than KC-E1 per window, median 161. The owner ruling of 2026-09-06 locks a control to its
treatment on the flight tokenizer, so that gap is now closed and the finding above is superseded.
Exposure row `SAEA-E21-KU-E1C-TOKEN-MATCH-V1`; receipt
`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-kc-e1-brief-44-v1/placebo-token-match/`;
built by `scripts/build_e21_brief_placebo_token_match.py` through `/tokenize` at zero generated
tokens, on the same chat template the prompt fit measured on, re-checked by digest before anything
was measured.

Each twin LINE is grown by whole repeats of one neutral one-token filler, `" item"`, until the twin's
rendered PREFIX through that line measures exactly what the brief's does — the mechanism
`rails.proposer._token_matched_control` already uses for the KC-A1 control, reached through the same
`token_counter` seam rather than a second implementation. Matching on prefixes rather than on
isolated lines makes whole-block equality a consequence rather than a hope: the prefix at the last
index is the whole block. **The brief is now token-equal on every one of the 44 calls at both caps** —
the whole brief (per-call median 2,102.5, max 5,893) and the flown cap 12 (median 451.5, max 676) —
asserted by measurement, per line and per call, not by construction. Cap 12 costs 6,110 filler
repeats across the 88 halves, a median of 5 per line.

The measurement is materialised as a hash-pinned artifact, `configs/knowledge/e21-brief-placebo-v2/`
`pad-plan-v1.json`, sha256 `e3b494d0…d49c`, 148,435 bytes, carrying per cap, per call and per half
the source bytes' sha256, the per-line pad repeats and both arms' prefix counts. **The flight needs
no tokenizer of its own**: the new evidence source `conec-class-lists-placebo-token-matched` replays
the repeats, and `DerivedEvidenceRegistry` re-derives the padded twin from the same ConEC bytes with
the exact repeats inside `params_hash`. KU-E1c's composed config hash moves from `17cf642e…` to
**`f1f63fce…`**. KC-E1's own baseline fragment is byte-identical to the one the fit measured, checked
with `git diff` against the fit's study commit rather than asserted; its composed hash reads
`3ac6d436…`, having moved from the fit's published `65825553…` at `fa357a24`, when the shared
experiment fragment's `mandatory_slices` note was rewritten to point at the prompt-fit receipt. That
edit moves both cells' composed hashes and neither cell's protocol.

**What the padding cannot reach, stated rather than hidden.** After the match the whole request text
is a constant **7 tokens LONGER** for the twin, on every one of the 1,593 windows — arm 454 / 673 /
855, twin 461 / 680 / 862 (min / median / max). That residual is the `[evidence <id>] ` HEADER of the
two blocks and not the brief: the arm names the `conec-class-lists-roster` / `-document` transforms
and the twin names their `-placebo-tm` ones, and a twin that named the arm's transforms would be
indistinguishable from it in a sealed trace. A constant 7-token surplus replaces a median 161-token
deficit, and a verdict should say so rather than claim a perfect match. The worst request after
padding is **3,058** against the 6,144-token slot — margin 3,086, factor 2.009 — so the cap-12 fit of
§7 item 2 still holds.


## 6. Budget

| | value | basis |
|---|---:|---|
| planned model calls | 3,500 | 1,593 windows × 2 cells = 3,186, plus 314 retry headroom; the comparator realized exactly 1,593 |
| planned speech audio seconds | 300,000 | 141,348.532 realized per pass × 2 = 282,697, rounded up |
| planned GPU hours | 3.2 | the comparator realized 0.973 GPU-h for one pass at this geometry; two passes is 1.95 before the brief. MEASURED since (§7 item 2): against the comparator's mean 1,215 prompt tokens per window, the CAPPED brief's text envelope is 454 to 855 flight tokens (median 673) where the comparator's was a constant 62, so the prefill roughly doubles rather than triples and 3.2 keeps its margin |
| paid API spend | 0 | unchanged and still in force |

Budgets are **run-cumulative across every attempt** of the run id. Re-measured on the preflight; the
flight **stops and reports** if the measured rate projects past 3.2 GPU-h.

The separately registered `SAEA-E21-TOOL-DIARIZATION-V1` (50 tool contacts, 145,000 audio seconds,
2.0 GPU-h, **zero frozen-core contacts**) is not part of this budget and is not a KC-E1 cost.

**2026-09-07 — the envelope is raised for the KC-E1 recovery, and the raise is headroom, not new
exposure.** KC-E1's first attempt `attempt-20260907T142632Z-a388ef` was killed at 42 of 44 calls, with
no seal and no score, when the host's low-memory watchdog took down the coordinator's serving wrapper
(`.wslconfig memory=56GB` on a 63.4 GB host; fixed by the owner the same day at `memory=44GB` with
gradual reclaim, plus the E7c host-memory instrumentation). That is an infrastructure failure, not a
model, protocol or data one, and it consumed the ONE recovery re-registration this flight is allowed:
a second failure stops the flight and the fix must be proven on a 4-row dry run first. Its spend is
durable and counts — **1,520 calls, 134,821.4766875 speech-audio seconds, 1.4993 realized GPU hours**
(the session monitor's wall clock over that attempt's own contact window, 5,397.478 s; 4,399.65 s
active, 997.82 s parked, 1,499 requests, mean 74.30 W). The run-cumulative rule therefore raises
KC-E1's own ceilings to prior durable spend plus its own worst case — **3,270 calls, 285,000
speech-audio seconds, 3.1 GPU hours** — while KU-E1c's are untouched at 1,750 / 150,000 / 1.6, so the
section 6 envelope for the two cells together becomes:

| | v1 envelope | after this amendment |
|---|---:|---:|
| planned model calls | 3,500 | **5,020** (KC-E1 3,270 + KU-E1c 1,750) |
| planned speech audio seconds | 300,000 | **435,000** (285,000 + 150,000) |
| planned GPU hours | 3.2 | **4.7** (3.1 + 1.6) |
| paid API spend | 0 | 0, unchanged and still in force |

**Nothing else moves.** The population, the split identity `fcc1b0bc…d69e`, the composed config hash
`3ac6d436…`, the protocol hash `da55a18d…`, the cap of 12, the arms, the one factor, the five manifest
scorers, the pairing unit, the strata, the guards and the decision rule of §5 are all exactly as
written above; the raise buys retry headroom for a re-flown pass and nothing else. It is not new
exposure: all 44 calls are exposed many times over (the flight row's inherited-exposure cell lists the
families), the recovery decodes the same windows with the same prompt, and **no byte of the dead
attempt is read, scored or paired** — scoring runs once per COMPLETE manifest and that attempt has
none. Recorded in `docs/exposure-ledger.md`: the dated recovery block at the head of the file and the
raised ceiling cells on row `SAEA-E21-KC-E1-BRIEF-44-V1`.

## 7. Preconditions — both closed

1. **`e21_participant_names` in D1 — CLOSED.** ✅
   The layer is registered through an additive, hash-pinned D1 **evidence** supplement,
   `saea-d1-evidence-supplement-v1`: `docs/receipts/artifacts/d1-e21-participant-names.json`, sha256
   `313da4c48acf7403207e2a45c28f90262a94adfaa42873a0c9f251fc9d6bfd83`, 44 rosters, 15,067 bytes,
   `ids_sha256` `81236a16…b51d6` equal to the carrier's own `e21_contexts` sample universe,
   `parent_d1_sha256` `9c10fad1…`. Exposure row `SAEA-SN-MF-E21-PARTICIPANT-NAMES-D1-V1`; receipt
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-participant-names-d1/`.

   Verified offline through the production rail on the real corpus: without the supplement an
   evaluation call's roster relpath is refused; with it all 44 resolve on both the file and the
   content rail; `conec-class-lists`' two items route to two different D1 layers and both pass; a
   tampered byte and a foreign sample id are refused.

   **A gate carries the base D1 identity plus AT MOST ONE supplement** (`FrozenCoreGate.__post_init__`).
   **KC-E1 carries this evidence supplement and no other** — it needs no media supplement, since all
   44 `earnings21-original` media entries are already inside the immutable D1 closure. All three
   fragments of the experiment now compose `configs/dataset/earnings21-discovery-conec-names.json`,
   which pins the supplement's path and digest.

   **A second defect was found and fixed while closing this.** `core.driver.run_experiment` ASSIGNED
   rather than accumulated the per-sample evidence relpath, so a source returning several
   carrier-bound items per sample had all but the last silently dropped — and `conec-class-lists`
   returns two, the roster and the document, with the **roster** being the one dropped. Without that
   fix the supplement would never have been consulted during this flight at all. Both rails and the
   binding context now take one value or an ordered tuple per sample, positionally paired;
   `tests/contract/test_multi_file_evidence_identity.py` tampers the roster half while leaving the
   document half clean — the case last-wins let through.

2. **Prompt fit on the flight tokenizer — CLOSED, and it cost the whole brief.** ✅
   Exposure row `SAEA-E21-KC-E1-PROMPT-FIT-V1`; receipt
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-kc-e1-brief-44-v1/prompt-fit/`;
   measured by `scripts/e21_kc_e1_prompt_fit.py` through `/apply-template` + `/tokenize` at zero
   generated tokens, on all 1,593 windows of both cells, with the audio replaced by the resident
   server's own opaque media marker.

   **The whole brief does not fit, and not narrowly.** KC-E1's uncapped text envelope runs 669 to
   **6,072** flight tokens (median 2,377); with 1,170 speech tokens for a 90-second window, the
   1,024-token completion ceiling and 2 special tokens the worst request is **8,268 against a
   6,144-token slot**. It fails the study's `slot_tokens >= 2 x worst_required` margin rule by a
   factor of 2.7 and it fails the STRICT fit by 2,124 tokens. The E5 receipt's whitespace maximum of
   2,565 understated the real envelope by **2.37x**, which is exactly why that receipt refused to
   guess.

   **`brief_max_entries_per_class` is 12 in BOTH fragments.** 12 is the LARGEST value on the
   preregistered grid whose worst request still satisfies the margin rule: worst required **3,051**,
   margin 3,093, factor **2.014**. The boundary is measured from both sides — 16 was rendered too and
   refused: its worst request needs 3,152 against the 3,072 the rule allows, so it fits strictly
   and fails the margin. Capped, KC-E1's
   envelope is 454 / 673 / 855 (min / median / max) and KU-E1c's is 412 / 518 / 599.

   "The smallest cap that fits" is read as the smallest INTERVENTION. Taken literally it is
   degenerate — the fit is monotone in the cap, so 1 always fits — and the receipt says so in writing.

   **The roster half is NOT disabled, and the cap's cost is published.** Model-free `cap-impact.json`,
   over the real 44: the roster half keeps **661 of 705** entries and the participant class — the one
   the PERSON hypothesis rests on — keeps **386 of 426** across 13 truncated calls. What the slot
   removed is the document half's residual-term class, 528 of 34,129 on all 44 calls, which this
   document already calls a recall aid rather than an inventory. The cell is still "the pre-meeting
   brief" and not "a keyword list".

   **One thing the flight must carry rather than assume: the twin is whitespace-matched, not
   token-matched.** KU-E1c's per-line whitespace counts equal KC-E1's on every call at every cap, as
   `core.class_lists.placebo_of` guarantees. On the FLIGHT tokenizer they do not: at cap 12 the
   placebo is 42 to 256 tokens **shorter** (median 161), because placeholder nouns cost fewer tokens
   than proper nouns and bracketed normalized forms. The cap shrinks that gap sevenfold from the
   uncapped median of 1,154; it does not close it. A verdict that reads the arm-versus-twin contrast
   as a pure content effect must say that the arm also carried a median 161 more prompt tokens.

   **CLOSED 2026-09-07 — see §5, "form twin token-matched on the flight tokenizer."** The paragraph
   above records what the prompt fit measured and stays as written; it no longer describes the
   committed twin. KU-E1c now renders token-equal to KC-E1 line by line and call by call at both
   caps, and the only remaining difference in the whole request text is a constant 7-token
   evidence-block header.

## 8. The flight agent's checklist, in order

1. **Diarization pass** — `SAEA-E21-TOOL-DIARIZATION-V1`, if it is to fly before this cell. It is
   independent of everything below and shares no GPU window with it: run it, or explicitly defer it
   under §4's read-time clause and say so in the flight receipt. Zero frozen-core contacts either way.
2. **Prompt fit** — precondition 2. **DONE** (2026-09-07, exposure row
   `SAEA-E21-KC-E1-PROMPT-FIT-V1`, receipt under
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-kc-e1-brief-44-v1/prompt-fit/`).
   `brief_max_entries_per_class` is **12** in both fragments; §7 item 2 carries the numbers and what
   the cap costs.
3. **Wire check** — **DONE** (2026-09-07, receipt under
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-kc-e1-brief-44-v1/wire-check/`,
   `scripts/e21_kc_e1_wire_check.py`). `saea-driver smoke --dry-run` for BOTH cells on a clean
   committed tree over the four shortest kb-construction calls, 61 windows each, zero sockets and
   zero model contacts. Confirmed: the two `[evidence …]` blocks arrive in roster-then-document
   order and the system message EQUALS the two blocks joined to the instruction (asserted on all
   6,460 rendered requests of the prompt fit, which is where the real transport can be driven —
   `LlamaServerTransport` re-checks session liveness on every send, so a contact-free check cannot
   drive it); `evidence_provenance` carries both relpaths, each routed by a REAL `FrozenCoreGate` to
   `e21_participant_names` and `e21_contexts` (the `_NoOpGate` a dry run uses skips that rail, so it
   is driven separately); the derivation registry accepts both records and every rendered half
   re-hashes to its transform's output at cap 12; the OBS tiling cut the roster receipt's own window
   count on every call with the stitch chains covering each contact exactly once; and the seal half
   verified with all five declared scorers producing aggregates. The placebo's per-LINE whitespace
   match is asserted by measurement in the prompt-fit receipt; its flight-token difference is
   reported there and is NOT zero (§7 item 2).

   **Re-run 2026-09-07 against the token-matched twin — PASS** (receipt
   `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-kc-e1-brief-44-v1/wire-check-token-matched/`,
   run id `SAEA-E21-KU-E1C-TOKEN-MATCH-V1`, study commit `85b64030`, clean tree, zero contacts of
   every kind). Every property above holds for the new `conec-class-lists-placebo-token-matched`
   source, and two of them answer the questions the repair raises:
   `every_half_rehashes_to_its_transform_output` — the derivation registry re-derives the PADDED twin
   from the same ConEC bytes and the same declared params, so the pad plan lives inside `params_hash`
   and inside the chain the gate re-proves — and `payload_key_set_equals_the_arm_allowlist`, so the
   new `evidence_pad_plan` key governs the render and never reaches the wire.

   **One pre-existing condition surfaced and left alone:** `fixed-legal-context` predates the
   2026-08-15 legality doctrine's either-field rule, so every run of it — this dry run and the flight
   alike — records provenance tier `UNVERIFIED` in the manifest's `legality` block, with a
   GRANDFATHERED declaration warning. That is a property of the arm, not of this cell, and closing it
   is not this flight's business; the flight receipt should carry the warning rather than be
   surprised by it.
4. **Register the exposure row** `SAEA-E21-KC-E1-BRIEF-44-V1` before the first contact — split
   identity `fcc1b0bc…d69e`, both cells, the §6 budget, the inherited exposure of these 44 calls — and
   **commit it** before takeoff.
5. **Fly both cells** under one build, one serving geometry, one audio path. One experiment in flight;
   at most one recovery re-registration, and a second failure stops the flight with the fix proven on
   a 4-row dry run.
6. **Score** each complete manifest once through `core.scoring_batch`, never sharded, under the four
   metrics plus cost. Then run `scripts/e21_window_pairing_read.py` on each cell's sealed outputs and
   trace to produce its per-window rows, and **refuse to proceed unless the re-aggregation check
   passes** — a cell whose window rows do not sum back to its own corpus numbers has a broken
   decomposition, not a result.
7. **Verdict** against §5: the pooled call-clustered CI90 as the decision interval, the window-level
   CI90 beside it labelled optimistic, the saves / harms / ties and sign test at n = 1,593, the
   per-class table with reference-word counts, and a per-stratum table for every stratum of §4 —
   speaker count, dominance class, sector and sample rate — under natural-mixture and equal-stratum
   weighting, on all 44 and on both halves of the E5 split.

## 9. What this document is not

It is not an authorization to fly. Both preconditions are now closed and the wire check has passed,
but the flight's own exposure row `SAEA-E21-KC-E1-BRIEF-44-V1` is unwritten and the owner's GO for
this cell is a separate act. It fixes the measurement so that when the cell does fly, the unit, the
estimator, the strata, the guards and the failure modes were all chosen before any result existed.

**What the flight agent inherits that this document did not originally anticipate.** The cell it will
fly is the brief capped at 12 entries per class, not the whole brief — the 6,144-token slot made that
choice, not a judgment about what the brief should contain. The margin at 12 is 2.014 against a rule
of 2.0, so there is no room to enlarge the brief at this geometry; enlarging it would need a larger
slot, which is a serving-geometry decision this document does not make and this preflight did not
take.
