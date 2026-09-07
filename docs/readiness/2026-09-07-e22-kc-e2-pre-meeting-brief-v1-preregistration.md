# KC-E2 — the Earnings-22 pre-meeting brief, whole prompt (v1)

**Status: PREREGISTERED, NOT AUTHORIZED TO FLY.** Two preconditions are open (§8), neither cell has
an exposure row, and the owner's GO is a separate act. Nothing here is an authorization.

**Read §9 before deciding whether to fly this.** The model-free source audit
(`docs/readiness/2026-09-07-e22-brief-source-audit-v1.md`, row `SAEA-E22-MF-BRIEF-SOURCE-AUDIT-V1`)
measured this brief's ceiling at **0.0229 corpus-WER points** against a same-request null of
**[−0.2356, +0.0692]**. The measurement was taken before the cell existed, exactly so this document
could be written with the answer to "is it worth a GPU hour?" in hand rather than after the fact.

Experiment fragment `configs/experiment/e22-kc-e2-brief-dev1500-v1.json`; arms
`configs/baseline/e22-kc-e2-brief-whole-prompt.json` (KC-E2) and
`configs/baseline/e22-ku-e2c-brief-placebo.json` (KU-E2c, the form twin); dataset fragment
`configs/dataset/earnings22-esb-dev1500-tail2s.json`, **byte-identical to the sealed comparator's**.
Owner context: the 2026-09-07 ruling that "once E22 is aligned it can be knowledge-enhanced too",
and the 2026-09-07 ruling on external sources restated in §1.

---

## 1. The knowledge source, and the rule

The brief is the call's own row of the Earnings-22 corpus metadata table
(`$SPEECHRL_DATA_DIR/datasets/earnings21-22/earnings22/metadata.csv`, 125 rows, sha256
`52dbda11f4abbabf1b59dedae315d5873d6ccfe75104d1bce3d8ab24341f28e1`), rendered as five labelled fact
lines: ticker symbol, country, UN region, major dialect family, language family and area. Each value
carries its Whisper-normalized form where casing or punctuation moves it — the same
`core.class_lists.annotate_normalized` the Earnings-21 brief uses.

**No external source is consulted, and the code cannot consult one.** Owner ruling, 2026-09-07:
Earnings-22 must not collect any external information, or the result stops being comparable with the
published Earnings-22 numbers this study aligns against. Accordingly:

* the company-name brief variant is **dropped**. It is not built, not registered and not
  preregistered;
* **no ticker → legal-name lookup table exists** in this repository, and none is created;
* `core.metadata_brief.BRIEF_FIELDS` names five columns of one corpus file and there is no field, no
  config key and no code path through which a sixth could arrive. `tests/unit/test_metadata_brief.py`
  asserts it, and the audit module asserts that its own only corpus input is that table.

The two remaining metadata columns — `File Length (seconds)` and `Sampling Rate (Hz)` — are
deliberately **not** rendered: they describe the WAV, not the meeting.

**What is never read**: no reference transcript, no ESB reference sentence, no `.nlp` file, no
force-aligned reference, no speaker list, no HALAS or annotation overlay, no segment table, no
roster gold column, no other call's audio.

### 1.1 Why this cell carries no D1 evidence supplement

The brief's evidence records carry `carrier_bound=False`, and that is a statement of fact rather
than a convenience. **Two structural refusals, either of which alone is decisive:**

1. `contracts.gate.FrozenCoreGate.__post_init__` allows **at most one supplement per gate**, media or
   evidence, never both — and this cell's dataset fragment must carry the `d1_media_supplement` that
   brings the `@ts2` clips into D1's identity closure at all. An evidence supplement would displace
   it.
2. `gate_evidence_identity._d1_evidence_supplement_manifest` requires a supplement's `ids_sha256` to
   **equal the carrier's own default evidence layer's sample universe**. `earnings22-original`
   declares no evidence layer (`data.carriers.EARNINGS22_ORIGINAL.evidence is None` — the ConEC
   Earnings-22 side is binary per-call PDF packets nothing here reads), and a 1,500-clip id set could
   not equal a 125-call one even if it did.

Underneath both: D1 records this table through `data.identity._csv_layer`, which registers 125 ids
and **no per-file manifest**, because a CSV layer has no per-sample files to hash. There is
therefore no D1-recorded per-sample evidence identity for the rail to check, and this source does not
pretend there is — the honesty `distractor-only-bias-list` and `derived-candidates` already state for
the same reason.

**What replaces it, and it is not nothing.** The table's bytes are pinned by path and sha256 in the
composed config (`evidence_brief_source`) and re-hashed on **every** read, so a corpus table edited
after the fragment was written is refused rather than silently flown; each item's
`DerivedEvidenceRecord` is re-derived by `DerivedEvidenceRegistry` from the call's own two-line
source slice before the flight opens a server; and the clip → call map the whole cell is paired by is
a committed receipt (`docs/receipts/artifacts/e22-dev1500-clip-call-map.json`, sha256
`c68aa0de…`) that re-checks its own `ids_sha256` and `map_sha256` on load.

## 2. The comparator, by name

`SAEA-E22-DEV-ESB-TAIL2S-V1`, attempt `attempt-20260907T090708Z-df36cc` — the `tail-silence-2s` arm
**admitted on all three clauses** by `docs/readiness/2026-09-07-e22-dev-encoding-probes-v1-verdict.md`
and recommended there as the Earnings-22 short-form serving default.

| | on these 1,500 published segments |
|---|---:|
| corpus WER % (`asr-wer-esb-whisper`) | **9.4054** |
| corpus WER % (frozen `saea-scoring-v1`) | 14.7640 |
| agentic error rate % (`analysis.e22_error_taxonomy`, DEV10 basis) | 1.7599 |
| boundary category mass (WER points) | 1.1085 |
| brief-term recall % (`brief-term-recall-v1`) | **87.23** (41 of 47 words) |
| reference words | 26,251 |

A knowledge cell must be measured on the serving surface the study actually recommends, or it
measures the encoding defect instead of the knowledge. That is why the comparator is the
tail-silence-2s arm and not arm A.

**The same-request null on this runtime and roster** is `−0.0844` corpus-WER points with CI90
`[−0.2356, +0.0692]` (2026-09-06 usage-cells verdict §3.2). Greedy decoding is not bitwise
reproducible across batch compositions here, so **the contrast is against sealed outputs and no
comparator is re-flown**; that interval is what "no effect" looks like on this instrument, and every
claim below is bound to it.

## 3. The pairing unit, and the cluster

**The paired unit is the published ESB segment (1,500 of them). The bootstrap cluster is the source
call (10 of them). The call-clustered interval governs; the segment-level interval is reported beside
it, explicitly labelled as the optimistic bound.**

Measured, not assumed: `SAEA-E22-MF-BRIEF-SOURCE-AUDIT-V1` §2 — 1,500 clips, exactly 150 from each of
the ten dev subset10 calls (4453225 / 4469088 / 4470684 / 4474506 / 4479944 / 4481952 / 4482383 /
4482613 / 4483937 / 4485192). The `@ts2` id folds to its published segment by splitting on `@`
(deviation `D-ENC-1`), which is what makes the join against sealed rows exact.

Estimator and knobs, fixed here: `analysis.paired.resampled_statistic` for the pooled ratios and
`analysis.paired.paired_contrast` for the descriptive saves / harms / ties, **seed 20260903, 10,000
replicates, CI90**, both weightings (natural-mixture and equal-call) reported side by side. Every
statistic is **pooled** `sum/sum`, never a mean of per-clip rates — a four-word clip must not weigh
as much as a forty-word one.

**The `n >= 400` rule.** This cell has 1,500 paired units and 10 clusters. The rule is met at the
unit the model contacts happen at, and the honest interval is the ten-cluster one. That is stated,
not finessed — and §9 says what ten clusters can and cannot resolve.

## 4. Strata

| stratum | source |
|---|---|
| **source call** (10) | the frozen roster receipt's own `stratum`, re-derived from each id and checked against it |
| utterance duration bucket | the roster's `audio_seconds`, the buckets `analysis.e22_usage_cells` already uses |
| dialect family (5 values) / UN region (4) / country (6) | the brief's own fields — reported because a dialect prior, if it exists, should show here first |

A stratum is a **reporting dimension, never a knob**. The decision rule of §5 conditions on none of
them.

## 5. Metrics and the decision rule

**Manifest scorers**, declared in the flight's own manifest and run once per complete manifest
through `core.scoring_batch`, never sharded: `asr-wer-esb-whisper` (paper-facing anchor),
`asr-wer-esb` (frozen `saea-scoring-v1`, beside it), **`brief-term-recall-v1`**, `cost`.

**Post-seal metrics**, computed from the sealed rows after scoring, exactly as the encoding probes
computed theirs: the semantic high-impact (agentic) rate and the boundary category mass through
`analysis.e22_error_taxonomy` at its committed version **on the DEV10 inventory basis, named in the
flight receipt** (the standing reporting obligation the 2026-09-07 verdict fixed), and
numeric-value accuracy. Numeric accuracy is post-seal rather than a manifest scorer for a structural
reason: `numeric-value-accuracy-v1` resolves a CALL's `.nlp` reference through `data.references` and
an ESB utterance is not a carrier sample, so it is computed here over the same hash-pinned ESB
reference layer the paper-facing scorer reads.

### 5.1 `brief-term-recall-v1`, defined here

Among a clip's reference words that lie inside a **brief term of that clip's own call**, the share
the hypothesis reproduces — pooled `sum(hits) / sum(brief-term reference words)`.

* **Normalization**: the vendored Whisper `EnglishTextNormalizer` on both sides and whitespace
  tokenization — byte-identical to `asr-wer-esb-whisper`'s, so a brief-term word is the same object a
  WER word is.
* **Terms**: the five fields of `core.metadata_brief.BRIEF_FIELDS` for the clip's OWN call, never the
  twin's. Both arms are scored against the same terms.
* **Coverage**: each term normalizes to a word tuple and is matched as a contiguous n-gram, longest
  first at each position, earliest field on a tie, left to right without overlap.
* **Recall**: the alignment is `scoring.wer.align`'s own; a covered reference word counts as recalled
  exactly when that alignment marks it a HIT.
* **Reported per field and per call**, always. A pooled number quoted without the per-field table is
  a number that is 49 % the word *other* (§9).

Model-free, deterministic, and already measured on the comparator before this cell existed.

### 5.2 The decision

> **ADMITTED** iff BOTH hold on the reported roster:
>
> 1. **corpus WER is non-inferior** — the call-clustered CI90 **upper** bound on the delta
>    (KC-E2 − comparator) is **<= +0.10 absolute points**; AND
> 2. **brief-term recall improves** — the call-clustered CI90 **lower** bound on the delta is
>    **> 0 against BOTH the sealed comparator AND the KU-E2c twin**.
>
> **NULL** if either brief-term-recall lower bound includes 0. A NULL with a positive point estimate
> against the twin and a negative one against the comparator is reported as "the form carried it",
> and the next cell is a supply-form question, not a content one.
>
> **HARMFUL** if guard 1 fails, with the failing guard named and the per-call and per-field tables
> published either way.

**The non-inferiority margin's provenance**: +0.10 absolute corpus-WER points, fixed here before any
number exists. It is deliberately **tighter** than the ±0.25 resolution the same-request null implies,
so the guard can only ever refuse a cell, never admit one on noise.

**Guards reported beside the rule, none of them gating**: the insertion share of errors and the
hypothesis-to-reference length ratio against the comparator's 26.93 % and 0.9963 (a brief that gets
read aloud shows up there first); the agentic rate; the boundary block; and the brief's measured
flight-token distribution with the twin's beside it.

**Reported whatever the outcome**: the ten-call table under both normalizers; both weightings; the
per-field brief-term table with reference-word counts; the call-specific versus shared-vocabulary
split of the term mass; S/D/I and length ratio; the utterance-duration decomposition; saves / harms /
ties with the exact sign test at n = 1,500; and both intervals of §3 with the optimistic one labelled.

## 6. Budget

Per cell — each of the two carries its own run id, its own exposure row and its own
`contracts.ExecutionPlan`:

| | planned | registered ceiling | basis |
|---|---:|---:|---|
| model calls | 1,508 | 1,600 | 1,500 rows × 1 contact + 8 canaries |
| speech audio seconds | 13,000 | 13,500 | 12,948.983 s for one pass, rounded up |
| GPU hours | 0.30 | **0.50** | the comparator realized **0.1188 GPU-h** for exactly this roster, geometry and audio path; the brief adds text tokens to a prompt whose cost is dominated by the live mmproj encode, so the realized figure should land near 0.15 h |
| paid API spend | 0 | 0 | unchanged and still in force |

Both cells together: **3,200 calls / 27,000 speech-audio seconds / 1.0 GPU-hours** of registered
ceiling. Budgets are metered **run-cumulatively across every attempt** of a run id, so a recovery
plan must cover prior durable spend as well as its own worst case; at most **one** recovery
re-registration per flight, and a second failure stops the flight with the fix proven on a 4-row dry
run.

## 7. What this cell cannot conclude

* **Nothing about Earnings-21.** The KC-E1 brief draws on ConEC participant rosters and press
  releases, a fundamentally richer layer. A NULL here is evidence about *this corpus's own metadata*,
  not about pre-meeting briefs.
* **Nothing about alignment.** These are dev numbers on a 1,500-row subset of this study's own dev
  split. The published 9.79 / 12.3 appear as orientation only, never as a difference.
* **Nothing about the test split.** No test read is taken, proposed or authorized. The reference
  loader is pinned to the DEV10 receipt; the six calibration-exposed ESB test calls are unreachable
  from the runner and the 109 confirmatory calls are not named, loaded or read.
* **Nothing about a diffuse accent prior.** If telling the core that a speaker is Indian- or
  South-African-accented improves words the brief never names, that lands on corpus WER and would
  still have to clear the ±0.25-point null. This cell measures the direct channel exactly and says so.
* **No superiority, generality or Stage-3 claim**; `paper-scale-confirmatory` is not available to this
  repository and is not requested.

## 8. Preconditions, both open

1. **PROMPT FIT on the flight tokenizer — OPEN.** `scripts/e22_kc_e2_prompt_fit.py` must render both
   cells' widest requests through the pinned GGUF chat template and satisfy this repository's own fit
   rule, `slot_tokens >= 2 × worst_required`, at `-c 40960 -np 8` (5,120 tokens per slot). The
   arithmetic says it will pass comfortably — the roster's longest clip is 34.88 s, so 455 speech
   tokens, plus a text envelope in the low hundreds, plus 1,024 completion and 2 special — but the
   number is measured, not assumed. It touches the resident server and is the flight agent's step;
   the script is written and unit-tested here (`tests/unit/test_e22_kc_e2_prompt_fit.py`).

2. **TOKEN-MATCHED PAIR — OPEN.** The owner ruling of 2026-09-06 locks a control to its treatment on
   the flight tokenizer. The same script writes `configs/knowledge/e22-brief-v1/pad-plan-v1.json`,
   and each fragment then takes a **two-key edit**: `evidence_source` moves to its `-token-matched`
   name and an `evidence_brief_pad_plan` pin is added. That moves each cell's composed config hash
   and nothing else about its protocol.

   **The padder here is SYMMETRIC, and that is forced rather than chosen.** KU-E1c's twin is a
   placeholder, always shorter than the proper nouns it replaces, so growing the twin always works.
   This twin is another REAL call's brief, and a real brief can be longer than the one it twins: the
   two Oceania calls render the corpus's shortest briefs — "Oceania" is the only one-word UN region —
   and **every** fact-distinct partner is longer. `core.metadata_brief.pair_pad_repeats` therefore
   grows whichever side is short at each line. Under the model-free whitespace measurement the arm
   gains **1 to 3** `" item"` repeats per line and the twin 0 to 2. What either side gains is token
   volume and **no fact, no name and no sector**; the one factor between the two cells stays the
   words in the five fact fields, and the verdict must state the filler counts rather than imply an
   unpadded arm.

3. **WIRE CHECK, request half — DONE and PASS; seal half deferred.** ✅/⏸
   `docs/checks/speech-aware-evidence-acquisition/2026-09-07-e22-kc-e2-brief-dev1500-v1/wire-check/`,
   study commit `b94c7d3c`, both cells, **1,500 contacts each, zero model contacts, zero servers,
   zero sockets**. `payload_keys_equal_arm_visible_fields` is **true** on both — the payload's field
   set is exactly `ARM_VISIBLE_FIELDS["bare-core"]`, the sealed comparator's own — the split identity
   equals the fragment's declared `8dc9d6a0…`, and the two cells' config and protocol hashes differ,
   which is what a one-key difference should look like. The evidence rail was driven end to end:
   **3,000 derivation records re-verified** by `DerivedEvidenceRegistry` against each cell's own
   declared params, `carrier_bound` `[false]` as §1.1 requires, the pinned table re-hashed on every
   read.

   **The seal-and-score half was REFUSED and that is the guard working.** The shared
   `$SPEECHRL_DATA_DIR/locks/flight.lock` is held by the live Earnings-21 flight
   `SAEA-E21-KC-E1-BRIEF-44-V1` (pid 10701, 17:12:38Z) recording the MAIN checkout's HEAD, and
   `core.bundle.git_commit` refuses to bind a COMPLETED manifest to a commit the flight never ran
   under. The lock was not touched. What that leaves unproven: the manifest builder, the bundle
   verifier and the four registered scorers over the canned responses. The flight agent re-runs the
   check with the seal half reached once the lock is free; the request half does not need re-proving.

4. **OWNER GO**, plus one exposure row per cell registered and committed before the first contact.

**One residual the verdict must carry, measured rather than assumed.** The two arms' evidence-block
HEADERS name different transforms (`e22-metadata-brief[-tm]` against
`e22-metadata-brief-deranged[-tm]`), so the whole request text stays a few tokens wider for the twin
even after the briefs themselves are token-equal. This is the same residual KU-E1c reported at 7
tokens, and it exists for the same reason: a twin that named the arm's transform would be
indistinguishable from it in a sealed trace. The prompt-fit receipt measures it per arm rather than
hiding it.

**The twin's pairing, and the defect it already caught.** The partner is chosen by
`core.metadata_brief.select_twin_partners`: for each roster call, the closest-measuring unused
Earnings-22 call **outside the roster** whose ticker, country, UN region and major dialect family
**all differ** from the arm's. Outside the roster, because a partner inside it could state a fact
that is true of another roster call. Fact-distinct, because the first pairing this repository built —
a plain cyclic derangement over the ten — handed call 4453225 a whitespace-identical partner that
restated its country, its region and its dialect family verbatim. That would have been a control in
name only. The pairing is materialised as the hash-pinned
`configs/knowledge/e22-brief-v1/derangement-v1.json` (sha256 `243e7052…`), verified pair by pair on
the flight tokenizer by the prompt-fit script and re-selected there only if a pair fails — and a
re-selection is written into the receipt, never applied silently.

## 9. What the audit says about this cell's power, before it flies

`SAEA-E22-MF-BRIEF-SOURCE-AUDIT-V1`, on this exact roster and this exact comparator:

| | value |
|---|---:|
| reference words | 26,251 |
| brief-term reference words | **47** (0.179 %) |
| comparator's recall on them | 87.23 % (41 hits, 5 S, 1 D) |
| **ceiling a perfect brief could move** | **0.0229 corpus-WER points** |
| call-specific share of the term mass | **0.00 %** |

Four consequences, all binding on the verdict:

1. **The term channel cannot carry a claim on this roster.** 47 reference words over 10 clusters,
   six of them wrong, with per-cluster denominators of 1, 2, 2, 2, 4, 5, 5, 6, 10, 10. Clause 2 of
   §5.2 is, here, a gate on six words, and no bootstrap over ten call clusters produces a usable
   interval on it.
2. **The corpus-WER channel is below the instrument's floor.** 0.0229 points maximum against a
   measured null of [−0.2356, +0.0692], and the 2026-09-07 encoding preregistration already binds
   that "a preregistered effect smaller than about 0.25 points on 1,500 rows cannot be distinguished
   from this null by one flight".
3. **Every brief term is shared vocabulary.** 23 of the 47 covered words are the literal word *other*
   — the `Major Dialect Family` value of four calls, a taxonomy label rather than a fact about the
   meeting, which also occurs 149 times in the other calls' references. Two are *cost*. Eight of the
   ten tickers never appear as a spoken word and no UN region name appears anywhere.
4. **A NULL is therefore the expected outcome, and it is not evidence that knowledge does not help
   this carrier.** It is evidence that *this corpus's own metadata table* is not a usable knowledge
   source for *its own transcription task*. The verdict must say that, in those words.

**The honest recommendation this document is willing to make**: fly this cell only if the owner wants
the negative result on the record with an interval attached. The engineering is complete and reusable
either way — the evidence source, the symmetric padder, the fact-distinct pairing rule and
`brief-term-recall-v1` all generalize to a richer Earnings-22 knowledge source, and none of them
depends on this cell flying.

## 10. What this document is not

It is not an authorization. It fixes the unit, the estimator, the strata, the metric, the guards, the
budget and the failure modes so that when the cell does fly — or is dropped — the choice was made
before any result existed. The audit that priced its ceiling is already on the record, and this
document does not argue with it.
