# KC-E1 — the Earnings-21 pre-meeting brief, whole prompt (v2)

**Supersedes `docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v1-preregistration.md`.** That
draft's §1, §2, §5 and §9 stand unchanged and are not restated here except where a number moves; this
document replaces its §3 (pairing), §4 (power), §7 (preconditions) and §8 (checklist), which is what
the owner's 2026-09-06 rulings and the three model-free rows landed since have changed.

**Status: PREREGISTERED, NOT AUTHORIZED TO FLY.** One precondition of v1 is now closed and one is
still open; §7 says which. Nothing here is an authorization.

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
  same entry count, same whitespace-token count per line, every entity token replaced by a
  position-chosen neutral placeholder. The two fragments differ in exactly one key,
  `evidence_source`;
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

## 6. Budget

| | value | basis |
|---|---:|---|
| planned model calls | 3,500 | 1,593 windows × 2 cells = 3,186, plus 314 retry headroom; the comparator realized exactly 1,593 |
| planned speech audio seconds | 300,000 | 141,348.532 realized per pass × 2 = 282,697, rounded up |
| planned GPU hours | 3.2 | the comparator realized 0.973 GPU-h for one pass at this geometry; two passes is 1.95 before the brief, and the brief roughly triples the prompt (comparator mean 1,215 prompt tokens per window; the brief adds a median 969 and a maximum 2,565 whitespace tokens) |
| paid API spend | 0 | unchanged and still in force |

Budgets are **run-cumulative across every attempt** of the run id. Re-measured on the preflight; the
flight **stops and reports** if the measured rate projects past 3.2 GPU-h.

The separately registered `SAEA-E21-TOOL-DIARIZATION-V1` (50 tool contacts, 145,000 audio seconds,
2.0 GPU-h, **zero frozen-core contacts**) is not part of this budget and is not a KC-E1 cost.

## 7. Preconditions — one closed, one open

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

2. **Prompt fit on the flight tokenizer — STILL OPEN.** ❌
   The brief runs **263 to 2,565 whitespace tokens** (median 969) against a 6,144-token slot whose
   certified worst request was 2,258 tokens; whitespace tokens are a lower bound on model tokens. The
   preflight must tokenize every call's brief with the FLIGHT tokenizer, report the per-call
   distribution beside the whitespace counts in the E5 provenance receipt
   (`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-pre-meeting-brief-provenance/`), and
   the worst-case total request. If it does not fit with the study's usual margin, set
   `brief_max_entries_per_class`, and **set it to the identical value in BOTH fragments** — the twin
   stops being a twin the moment the two cells cap differently. The value goes into both fragments and
   into the flight receipt.

   **Do not fly with the roster half disabled.** Dropping it changes the cell from "the pre-meeting
   brief" to "a keyword list", which is a different question and already has an arm
   (`conec-contexts`).

## 8. The flight agent's checklist, in order

1. **Diarization pass** — `SAEA-E21-TOOL-DIARIZATION-V1`, if it is to fly before this cell. It is
   independent of everything below and shares no GPU window with it: run it, or explicitly defer it
   under §4's read-time clause and say so in the flight receipt. Zero frozen-core contacts either way.
2. **Prompt fit** — precondition 2. Tokenize all 44 briefs and both cells' full requests on the flight
   tokenizer; set `brief_max_entries_per_class` identically in both fragments if needed; land the
   measurement as a receipt. **The flight does not take off until this is a committed number.**
3. **Wire check** — a 4-row dry run through the committed launcher path on CONSTRUCTION calls only.
   Confirm: two `[evidence …]` blocks arrive in roster-then-document order; `evidence_provenance`
   carries both relpaths; the derivation registry accepts both records; the gate's evidence rail sees
   **both** relpaths for each sample and routes them to `e21_participant_names` and `e21_contexts`
   respectively (this is what precondition 1's fix makes observable — check it explicitly); and the
   placebo cell's requests match the arm cell's token counts line for line.
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

It is not an authorization to fly. Precondition 2 is open, the exposure row is unwritten, and the
owner's GO for this cell is a separate act. It fixes the measurement so that when the cell does fly,
the unit, the estimator, the strata, the guards and the failure modes were all chosen before any
result existed.
