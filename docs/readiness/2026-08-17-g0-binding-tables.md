# G0 binding tables — P-A2T and P-SLU

Date: 2026-08-17. Status: **BINDING TABLES — inputs for registration, not a registration.**
Nothing here registers a probe, opens a split, authorises a touch, or fixes a threshold. The
coordinator pins numerics and registers; these tables supply the mechanical values the two
pre-registration drafts mark `[TBD]`, plus the defects found while deriving them.

Method and exposure: **CPU only, zero model contact, no flights, no exposure rows.** Every number
below comes from reading metadata, registry files, split receipts and already-consumed artifacts.
The only artifact read that is not a plain file read is an **archival replay** of two consumed
Audio2Tool baseline blobs out of the cold-backup bundle mirror — pre-authorised under owner ruling
D5, no inference re-run. Nothing was written outside this repository's `configs/probes/g0-binding/`
and this file.

Machine outputs:

| File | Contents |
|---|---|
| `configs/probes/g0-binding/pa2t-binding.json` | P-A2T split identity, A0 reuse verdict, legality findings, proposed arm redefinition, timing basis |
| `configs/probes/g0-binding/pslu-sample-devel-n60.json` | the seeded P-SLU devel draw: 60 items, split identity hash, per-item media and duration |
| `configs/probes/g0-binding/pslu-rosters-train-only.json` | P-SLU arm rosters A1/A2/A3 and the A4 derangement map, train-split-only provenance |

These are drafts. No flying config is final until the coordinator registers.

---

## Part 1 — P-A2T binding table

### 1.1 Split identity — verified clean

The frozen discovery receipt exists and is internally consistent.

| Field | Value |
|---|---|
| Receipt | `docs/receipts/probe-samples/r1-audio2tool-sample.json` |
| Probe | `R1-audio2tool-direct` |
| Split identity hash | `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` |
| Split role | `discovery` |
| Seed | 20260807 |
| Items | 400 (50 per tier x 8 tiers) |
| Pool | 30,733 |
| Cross-check | all 400 receipt items resolve in their tier manifests with matching `query_idx` |

The prompt template `configs/probes/r1_audio2tool_direct.txt` re-hashes to
`8ea2849d9f1d948ab46734fdc99e37efaba0b78216fdd2add0f8fccb3997da9a`, matching
`configs/probes/manifest.json`. Both identity anchors the draft needs are therefore intact.

### 1.2 A0 reuse verdict — **RE-FLY REQUIRED**

The draft's arm A0 may reuse consumed T2 results "ONLY if protocol hash + split identity match
exactly". They do not match, because **no artifact for any Audio2Tool read on the 400-item
discovery split exists anywhere.**

Searched exhaustively and empty — unbounded recursive greps over `runs/`, `attempts/`, `derived/`,
`logs/` and `manifests/`, including the multi-GB `*.trace.jsonl` bodies, all returned zero hits for
the split identity hash, for `tool_accuracy`, and for `audio2tool`. Also empty: all 89 run
directories under `$SPEECHRL_DATA_DIR/runs` (no a2t run, no `outputs.jsonl`, no `scores.json`, no
`ExecutionPlan` declaring `carrier_lock_key: audio2tool`); `docs/exposure-ledger.md` (no a2t row);
`docs/checks/**` (no a2t receipt); and a depth-7 name search across the whole data root (no a2t-named
entry outside `datasets/audio2tool`).

**Proven, not inferred: the frozen 400-item split was never bound to any execution on this machine,
and the consumed T2 read left no artifact of any kind.** Everything the study holds for Audio2Tool
is pre-flight — receipt, manifest, prompt template, loader, scorer, rails adapter, and the draft.

The only recoverable Audio2Tool reads are two consumed W1-era baselines, replayed from
`program-archives/mirrors/speech-mllm-training-free-rl.git`
(`_repro/baselines/audio2tool__qwen3-omni-30b-gguf__{dev,test}.json`). Every identity field
disagrees with the frozen protocol:

| Dimension | Frozen R1 protocol | Archived dev blob | Archived test blob |
|---|---|---|---|
| Split | discovery, 400 items | `dev`, n=40 | `test`, n=60 |
| Seed | 20260807 | 20260705 | 20261705 |
| Model | Q4_K_M GGUF (study runtime) | Q8_0 GGUF, `-ngl 28` | Q8_0 GGUF, `-ngl 28` |
| Decode | greedy, temperature 0 | temperature 0, top_p 0.95, top_k 40 | same |
| Prompt | full 152-tool registry | **only the sample's gold tool** (one registry line) | same |

Zero fields match. **A0 must be re-flown in-block** — the fallback the draft already anticipates.

### 1.3 Headroom extraction — **not possible from existing artifacts**

| Quantity | Value |
|---|---|
| Headroom samples (tool correct, EM failed) on the discovery split | **0 available — no per-sample record exists** |
| Proposed n | **cannot be bound now** |
| Archived analogue headroom, dev n=40 | 1 item |
| Archived analogue headroom, test n=60 | 1 item |

The archived reads cannot stand in: their prompt ships only the gold tool, so argument matching sat
at 97.5% / 98.3% and almost nothing landed in the "tool right, answer wrong" cell.

**Proposed sequence instead of a binding.** Fly A0 on the frozen 400 (or a seeded tier-stratified
subset), score with `a2t-scorer-v1`, then select the headroom set
`{tool_accuracy == 1.0 AND exact_match == 0.0}`; if that set exceeds 40, draw n = 40 by seeded
tier-stratified sample at seed 20260807. This makes P-A2T a two-block probe, not a single flight.

### 1.4 The cited headroom premise is unsourced

The draft's section 1 states "tool-acc 84.6% vs EM 15.6%" as measured. That pair has no artifact
behind it; it appears only as prose, and every recoverable measurement contradicts it:

| Source | Tool-name accuracy | Joint score |
|---|---|---|
| Archived dev, n=40 | 67.5% | 65.0% |
| Archived test, n=60 | 86.7% | 85.0% |
| Claimed "T2 discovery read" | 84.6% | 15.6% (EM) |

An exact-match rate of 15.6% against a tool accuracy of 84.6% is the entire motivation for the
probe. It must be re-derived from a real A0 flight before it can motivate anything.

### 1.5 Legality findings — arms A1/A2/A3 do not hold as drafted

Three mechanical facts, all verified against the shipped data and the loader:

1. **The per-sample `functions` field is gold.** Every tier item ships a `functions` list whose
   members are exactly the expected tool(s): size 1 on tier1/2/4/5/6/7, and 2–5 on tier3 and tier8
   matching the expected call count. Any roster keyed on `functions` is **ceiling tier** and is not
   flyable under the draft's own section 5.
2. **A0 already ships the entire pool.** `render_tool_schemas` fills `{tool_schemas}` with all 152
   registry rows and all eight columns — `argument_defaults` and `argument_constraints` included
   (92 of 152 tools carry non-empty constraints). Arm A3, "full task entity pool, no per-sample
   targeting", is therefore **byte-identical to A0**.
3. **No legal-tier per-sample targeting source exists.** The task-native keys are `domain`,
   `category` and the global registry. Nothing shipped identifies this sample's relevant tool
   without using gold.

Consequently A1 ("exact roster ... task-native legal provenance") and A2 ("exact + K distractors")
have no legal construction, and A3 is a no-op arm.

### 1.6 Proposed redefinition — a compaction ladder

Because A0 already supplies the whole 152-tool pool, the only available legal manipulation is
**narrowing, not adding**. That is the draft's own kb34 question, correctly oriented.

| Arm | Supply | Entries | Est. prompt tokens | Tier |
|---|---|---|---|---|
| A0 (= A3) | full 152-tool registry — status quo | 152 | ~12,693 | legal |
| A1' | the registry row of the tool **the core itself named** in its A0 pass | 1 | ~200 | self-supplied (legal) |
| A2 | A1' row + K = 9 distractor rows | 10 | ~1,000 | legal |
| A4 | another sample's A1' row, length-matched | 1 | ~200 | control |
| A1 (oracle) | the sample's own `functions` rows | 1–5 | ~200–500 | **ceiling — not flyable here** |

Collapsing A0 and A3 saves a whole arm. A1'/A2/A4 all depend on the A0 pass, which reinforces the
two-block sequence in 1.3. K = 9 keeps the diluted arm well below the 50–100-entry dose window
while staying an order of magnitude above A1'; distractors draw at seed 20260807, same domain where
possible. Registry domains for distractor drawing: `smart_car` 86, `smart_home` 53, `wearables` 13.

Rosters carry **no gold-derived field** under this construction: A1'/A2/A4 content is task-shipped
registry text, and the *selection* is the frozen core's own output, not a dataset annotation. That
is the E1' semantics the draft asks for — but only under this redefinition, not as drafted.

### 1.7 Timing basis

| Quantity | Value |
|---|---|
| Feature cache state | **cold** for audio2tool (0/350 coverage, measured 2026-08-17) |
| Items with top-level duration | 350 of 400 (tier7 carries per-turn media) |
| Audio total (those 350) | 1,801.3 s = 30.0 min |
| Mean / max per item | 5.147 s / 15.417 s |
| First-arm warm cost | ~350 encoder chunk-forwards, ~82.5 MiB; later arms hit the cache |
| **A0 prompt size** | 50,770 chars ≈ **12,693 estimated tokens per request** |

Prefill, not audio, dominates: every A0 request carries the whole registry. The narrowed arms cut
the prompt by roughly 60x, so they are far cheaper than A0.

**GPU estimate (assumptions stated, not measured).** At an assumed 2,000–5,000 tok/s prefill for
Q4_K_M 30B-A3B plus audio encode and a short decode, A0 costs roughly 4–11 s per request:

| Block | Requests | Estimate |
|---|---|---|
| A0 on the full 400 | 400 | 0.45–1.2 GPU-h |
| A0 on a seeded 120-item subset | 120 | 0.13–0.37 GPU-h |
| A1' + A2 + A4 at n = 40 | 120 | 0.03–0.10 GPU-h |
| Silence-swap spot control | ~3–5 | negligible |

Total for the full-400 route: **≈ 0.5–1.3 GPU-h**. The draft's stated 0.1–0.25 GPU-h understates
this by roughly 3–6x, because it did not account for the 12.7k-token registry prefill on every
request. A 3-sample timing smoke should pin the per-request cost before the budget is registered.

### 1.8 Governance note for the coordinator

The 2026-08-15 owner amendment admits **one** bounded Audio2Tool probe, specified as
"2x2 {tool-registry roster injected, not} x {clean, noisy}, tiers 2-3 subset, EM primary / WER
secondary". The draft's five-arm precision ladder across all eight tiers is a different
factorization: it has no {clean, noisy} axis and is not tier-2/3-scoped. That gap is the
coordinator's to reconcile — either map the design onto the approved 2x2 or seek an amendment.
Flagged, not resolved here.

### 1.9 P-A2T blockers

- **B1** — the section 1 headroom premise (84.6% / 15.6%) is unsourced and contradicted.
- **B2** — A0 cannot be reused; no artifact exists on the frozen 400-item split.
- **B3** — the headroom sample list cannot be extracted, so n stays unbound.
- **B4** — A1 and A2 as drafted have no legal-tier per-sample source; `functions` is gold.
- **B5** — A3 as drafted is byte-identical to A0.
- **B6** — the arm design does not match the shape the owner amendment approved (1.8).

---

## Part 2 — P-SLU binding table

### 2.1 The seeded devel sample — drawn, verified, hashable

| Field | Value |
|---|---|
| Carrier / lock key | `slurp`, revision `8eb16545762be97ace75334109d73824217311f1` |
| Metadata | `$SPEECHRL_DATA_DIR/datasets/slurp/metadata/`, `devel.jsonl` sha256 `00d346b1…`, `train.jsonl` sha256 `4a05a3de…` |
| Split / role | `devel` / `discovery` (`test` held out; the loader refuses it without an explicit flag) |
| Seed | 20260807 (the program-wide probe-sampling seed) |
| n | **60** |
| Split identity hash | `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` (sha256 over the newline-joined sorted `sample_id` list) |
| Real audio only | yes — every item resolves under `slurp_real`; 0 synthetic |
| Media existence | **60/60 flac files present on disk**, durations read from the flac headers |
| Audio total / mean | 182.26 s / 3.038 s (min 1.408 s, max 6.208 s) |
| Gold slots in the sample | 89 (mean 1.48 per utterance) |
| Distinct utterances | 60 (one recording per `slurp_id`) |

Devel context: 2,033 utterances expand to 8,690 recordings (4.27 per utterance) across 18
scenarios, 24,847.3 s of audio in total.

**Selection rule (pinned).** Scenario-stratified over all 18 devel scenarios, largest-remainder
allocation with a floor of 1, restricted to **entity-bearing** utterances (at least one gold slot);
within a scenario, `random.Random(f"{seed}:{scenario}").sample` over the id-sorted pool; one
recording per utterance via `random.Random(f"{seed}:{scenario}:{utterance_id}")`.

The entity-bearing restriction is a deliberate, declared choice, exactly parallel to P-A2T's
headroom targeting: only 68.2% of devel utterances carry any slot at all, and an unrestricted draw
gave 20 of 60 samples with zero gold slots and only 61 gold slots overall. Restricting lifts the
sample to 89 gold slots with no zero-slot items, which is what the primary metric needs. **Gold slot
counts are used for SELECTION ONLY and never enter any supply path.** If the coordinator prefers
the unrestricted draw — it is the better false-positive control, since a zero-slot utterance
detects spurious slot induction directly — that variant is reproducible from the same script by
dropping the restriction, and both are reported.

Allocation across scenarios: calendar 8, play 7, qa 5, email 4, transport 4, weather 4, datetime 3,
iot 3, news 3, recommendation 3, social 3, alarm 2, cooking 2, general 2, lists 2, music 2,
takeaway 2, audio 1.

### 2.2 Legality finding — `train_synthetic` leaks the devel surface

The draft states that SLURP "is legality-clean by construction: rosters are mined from the TRAIN
split ontology, fully disjoint from the devel evaluation surface". That is true of `train.jsonl`
and **false** of `train_synthetic.jsonl`.

| Check | Result |
|---|---|
| devel `slurp_id`s also in `train.jsonl` | **0** — clean |
| devel `slurp_id`s also in `train_synthetic.jsonl` | **1,317 of 2,033 (64.8%)** |
| …of those, identical `sentence` | 1,317 (all) |
| …of those, identical entity set | 1,317 (all) |
| Ontology values reachable only via `train_synthetic` | 1,281 |

`train_synthetic` is the TTS rendering of a sentence pool that includes the devel sentences, so it
carries devel's own gold fillers verbatim. This matters beyond the probe: the shipped
`data.slurp.load_slurp_ontology` mines `train` **and** `train_synthetic`, and
`rails.adapters.slurp.SlurpAdapter.build_query` renders that ontology as the task-native query. As
built, the adapter's own baseline query is therefore **ceiling tier, not legal tier**.

Every roster in `pslu-rosters-train-only.json` is mined from `train.jsonl` alone. The adapter defect
is reported here, not repaired — it is a code change outside this mission's scope, and it needs the
coordinator's decision on whether the fix is a loader flag or a change of default.

### 2.3 Train-split ontology

| Scope | Entity types | Distinct values |
|---|---|---|
| `train` only (**used**) | 55 | 4,157 |
| `train` + `train_synthetic` (**refused**) | 56 | 5,438 |

Largest types by occurrence: `date` (289 values / 1,823 occurrences), `place_name` (482 / 1,088),
`event_name` (351 / 1,000), `person` (468 / 866), `time` (237 / 799), `media_type` (91 / 478).
Per scenario, the train ontology holds 7–26 entity types (mean 14.5).

### 2.4 Arm rosters

Token counts are `ceil(chars/4)` estimates, labelled as estimates throughout.

| Arm | Construction | Entries | Est. tokens |
|---|---|---|---|
| A1 | per scenario: top-5 train values per entity type, round-robin capped at 40 entries | 19–40 (mean 35.6) | mean ~188 |
| A2 | every train entity type name, no values | 55 | ~184 |
| A3 | global train ontology, type-round-robin by frequency, **dose-capped at 100** | 100 | ~583 |
| A4 | another scenario's A1 roster, paired by adjacent size | 19–40 | mean ~188 |

**A3 dose cap: propose 100.** The uncapped ontology is 4,157 entries ≈ 24,931 estimated tokens —
far outside any usable window, so a cap is mandatory rather than optional. 100 sits at the top of
the 50–100-entry degradation window, which is where the dose law predicts A3 should underperform
A2. The round-robin construction keeps all 55 types represented at cap 100 (depth 2).

**A1 is deliberately held below the dose window** (cap 40) so that A1-vs-A3 reads as a precision
contrast rather than a confounded dose contrast. Without the cap, top-5 alone would push six
scenarios (play 100, calendar 63, email 60, transport 59, general 56, recommendation 50) into the
window.

**A4 derangement** (no fixed point, paired by adjacent capped size): audio↔cooking, datetime↔weather,
alarm↔takeaway, news↔iot, lists↔music, social↔qa, recommendation↔general, transport↔email,
calendar↔play. Mean entry-count delta 1.67, max 8 — tight length matching.

### 2.5 Feasibility check — is there anything for A1 to convert?

Scoring-side aggregate over the 60 sampled utterances' gold slots, computed for feasibility and
**never written into a roster or prompt**:

| Ontology scope | Slot-value coverage | Slot-type coverage |
|---|---|---|
| `train` only (used) | 76.4% (68 of 89) | 100% |
| `train` + `train_synthetic` (refused) | 92.1% (82 of 89) | 100% |

76.4% is a healthy ceiling: the legal roster can in principle supply the right value for about
three quarters of the gold slots, leaving genuine headroom without making the task trivial. The gap
to 92.1% is precisely the leak quantified in 2.2 — a useful measure of how much the contaminated
ontology would have flattered the result.

### 2.6 GPU estimate

Prompts are small on every arm (A0 instruction only; A1 ~188, A2 ~184, A3 ~583 estimated tokens)
and audio averages 3.0 s, so per-request cost is low and the feature cache warms on arm 1.

| Configuration | Requests | Estimate |
|---|---|---|
| 5 arms x 60 + ~5 silence controls | ~305 | **0.13–0.34 GPU-h** |
| 6 arms (A1 and A1' both) x 60 + controls | ~365 | **0.15–0.40 GPU-h** |

Comfortably under 1 GPU-h, consistent with the draft. A 3-sample timing smoke still pins it.

### 2.7 Binding decisions left to the coordinator

- **A1 versus A1'.** The draft flags that scenario scoping from the gold scenario makes A1
  ceiling-tier at the scoping step. That remains true and is unchanged by this pass. The rosters
  shipped here are scenario-keyed, so they serve either arm: A1 uses the gold scenario, A1' uses the
  scenario the core predicts in a first pass. Flying both costs ~60 extra requests (2.6).
- **Restricted versus unrestricted devel draw** (2.1).
- All threshold values in both drafts' branch rules — this pass deliberately proposes none.

---

## Part 3 — reproduction

Every number here was produced by scripts run in WSL2 `Ubuntu-24.04` under `~/.venvs/speechrl` with
`PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=<repo>/src` (no install, no venv mutation). The scripts
live in the session scratchpad, not in the repository, because they are derivation tools rather
than probe code; the coordinator should promote whichever ones become flight-path code through the
normal review. The two SLURP JSONs regenerate deterministically from `seed = 20260807`; the
P-A2T JSON is derived from the frozen receipt, the registry and the replayed blobs.

Archival replay provenance: blobs `9d7da43c2d68fb44165951ac8932c9fad1125233` (dev) and
`35ce686a8822ac6bf35581805a5941c09a704318` (test), read via `git cat-file` from
`$SPEECHRL_DATA_DIR/program-archives/mirrors/speech-mllm-training-free-rl.git`. No inference was
run and no repository was modified by the replay.
