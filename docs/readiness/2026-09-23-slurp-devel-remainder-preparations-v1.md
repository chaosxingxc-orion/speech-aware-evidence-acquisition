# SLURP DEVEL-REMAINDER preparation plan, v1

> **Sections 0-9 are the v1 record and their roster-bound numbers are SUPERSEDED by
> [section 10, "v2 carve-out"](#10-v2-carve-out-provisional-decision-109).** The coordinator ruling
> of 2026-09-23 (provisional decision 109) carved the 60 `reserved-final-unread` FINAL60 recordings
> and the 60 already-contacted historic probe-60 recordings out of the remainder, so the live roster
> is `SLURP-DEVEL-REMAINDER-V2` (6,570 rows), not the `…-V1` named below. V1's receipt, runtime view
> and check artifacts stay committed exactly as they were frozen and are **never rewritten** -- the
> committed documents that pin their file hashes would break -- so every v1 number below is left
> standing as the parent record and section 10 states what replaced it. Nothing here has been
> contacted: all four ledger rows are still DRAFT with `consumed = no`.

Owner decision 107 of 2026-09-23 (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`):
the development side may expand up to the full SLURP `devel` split as the development-side
validation resource, prepared with the same pipeline as DEV-2000-ADDED, built in parallel ahead of
time and fast. This document states what that expansion needs before it can fly, and what each step
will cost. It registers no cell, authorises no contact and flips no readiness state. Every number
below was measured model-free in worktree `/home/chao/saea-worktrees/fable-s3dev` (branch
`fable/s3dev`) on the base master `a2561ae5`: zero model, tokenizer, encoder, embedder, scorer, GPU
and network contacts, and no audio sample was decoded.

Precedent throughout: the DEV-2000-ADDED preparation chain of cell B6
(`docs/readiness/2026-09-21-slurp-b6-dev2000-added-preparation-plan-v1.md`) and the Stage-3
construction chain of R01 (`docs/readiness/2026-09-22-slurp-stage3-construction-r01-preparations-v1.md`).

## 0. The roster in one paragraph (v1; superseded by section 10)

`SLURP-DEVEL-REMAINDER-V1` (`docs/receipts/rosters/slurp-devel-remainder-v1.json`, raw sha256
`83f618bdadf338fe88ae0a851d43ce4c9e3ef9569365fd7bf2bcffb82cb4ee18`): **6,690 SLURP `devel`
recordings of 1,839 utterances** -- every devel recording that is in neither the sealed DEV-1000
(`docs/receipts/probe-samples/DEV-1000.json`) nor SLURP-DEV-2000-ADDED-V1. Take-all freeze through
`core.roster.freeze_roster` (quota == each scenario's surviving capacity, the 2,000 sealed
recordings as `exclude_sample_ids`, seed 20260923, `roster_role: evaluation`, `split_role: dev`,
`stratum_withheld_per_item: true`, `target_gold_opened_before_receipt: false`), split identity hash
`e65cd3b1842e7a4c1d8cab39b86278166b45e22c0c4d5f5c3f707724dc2e4fdc`. **Audio: 18,978.9523125 seconds
total** (5 h 16 min; mean 2.837 s, min 0.512 s, max 13.166 s), 3,235 headset / 3,455 far-field,
359,107,433 media bytes, all 18 scenarios present. The declared ceiling everywhere below is
`18979` (`ceil(18978.9523125)`), the form the DEV-2000-ADDED and R01 plans used. Runtime view
`configs/dataset/slurp-speech-native-devel-remainder.json` (raw sha256
`192a214408c098458adcf8d9471cc1a966e332aaa5e3d1888dce87977181791e`, canonical `runtime_view_sha256`
`5ecda759a387e8b13de7a1236234ac77be5ff82dc4d3ab9a816eeb2ab636d20b`).

**The expanded DEV read is the complete devel split.** Proven in the receipt's `completeness` block,
id by id: DEV-1000 (1,000) + DEV-2000-ADDED (1,000) + DEVEL-REMAINDER (6,690) = 8,690 = every devel
recording, and the three parts are pairwise disjoint. The DEV ladder nests inside the two sealed
halves (DEV-100 < DEV-500 < DEV-1000, and the reserved DEV-500-B < DEV-2000-ADDED), so excluding the
two rosters excludes every rung with them and nothing else has to be subtracted.

**No D1 media supplement is needed, and that is the gate's own answer.** The runtime-view builder
constructs a `contracts.FrozenCoreGate` with NO D1 media supplement configured and calls the gate's
own reader, `assert_media_identity_closure` / `media_identity_closure_ids`: the base D1 identity
artifact `docs/receipts/artifacts/d1-identity.json` declares **8,690** SLURP media ids, all 6,690
roster rows are inside that closure, and every row's measured bytes and SHA-256 equal D1's record.
The view therefore carries `d1_media_supplement: null`, `d1_media_supplement_sha256: null` and
`d1_manifest_sha256: null`, and the driver's own `--preflight-only` confirmed **D1 media identity
PASS for 6,690 samples**.

## 1. Coverage finding: how many DEVEL-REMAINDER rows already have packets or a warm cache (v1; superseded by section 10)

**0 of 6,690 rows are promoted. 60 of 6,690 are warm in the legacy feature cache, and they are
exactly the historic probe-60.**

Method (id level only; no packet byte and no `.feat` file was read for the promotion audit): every
JSON document under the resident packet root `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a` was
parsed for its `packets[].packet_id` set and intersected with the 6,690 roster `packet_id`s
(`sample_id` with `:` replaced by `/`); the result was confirmed against the on-disk leaf
directories `slurp/devel/<utterance>/<recording>` under the same root. Cache warmth is the FNV-1a
key of each media file's bytes (`core.model.speech_features.legacy_audio_feature_cache_key`), so it
is a property of the file, not of a prompt.

| Promotion receipt inspected | packets | DEVEL-REMAINDER rows covered |
| --- | ---: | ---: |
| `DEV-100` / `DEV-500` / `DEV-1000` / `DEV-2000-ADDED` | 100 / 500 / 1,000 / 1,000 | 0 |
| `EVO-FOLD-A-V2` / `EVO-FOLD-B-V2` / `EVO-FOLDS-V2` | 1,080 / 1,080 / 2,160 | 0 |
| `STAGE3-CONSTRUCTION-R01` | 800 | 0 |
| `TRAIN90` / `GATE18` / `GATE-C36` / `OPT-A36` | 90 / 18 / 36 / 36 | 0 |
| `EFFECT-C108` / `EVIDENCE-E108` / `FACTOR-D108` | 108 / 108 / 108 | 0 |
| `KEY18` / `OPT-B18` / `ENG-GATE8` / `SLURP-KNOWLEDGE63` | 18 / 18 / 8 / 63 | 0 |
| **union of every receipt under the root** | | **0** |
| on-disk `slurp/devel/**` leaf packet directories | 2,000 | 0 (the two sealed halves) |

That is exactly what the subtraction predicts: the only devel packets that exist are DEV-1000's and
DEV-2000-ADDED's, and the remainder is defined as what is in neither.

**Consequence for preparation 1.** The ENCODE step contacts **all 6,690 rows**:
`scripts/slurp_evo_fold_preprocess.py` drives one contact per roster row and does not skip warm rows
(a warm row is cheap but still a contact). The 60 probe-60 rows are re-contacted with everything
else; PROMOTE will create 6,690 new packet directories and touches no existing one.

## 2. The np8 geometry-equivalence preflight (it gates preparation 1)

Decision 107 asks for the expansion to be prepared **fast, with more workers**. Today `--workers` is
documented as "the sidecar serves -np 4" and the sidecar fragment
`configs/model/q4km-preprocess-featcache-cpu-sidecar.json` pins `-np 4`, so asking for more workers
than that only queues requests inside the server: it looks like throughput and is not. The honest
version of "more workers" is more SLOTS, and more slots change how the server batches -- and **no
sealed SLURP speech packet was ever produced at `-np 8`**. The equivalence is therefore measured
before the 6,690-row pass relies on it.

* **Sidecar fragments**: `configs/model/q4km-preprocess-featcache-cpu-sidecar-np8.json` (raw sha256
  `3bf04cfbc4168ec9b105d5d6f97ba50921212475bb85256ad3b5b6be3a2ac798`) is the sealed np4 fragment with
  exactly one value changed, `-np 4` -> `-np 8`; a test asserts that difference set.
  `...-np8-scratch.json` (`57db716f6d50eedbb828bf3c98769b679795941396fde55c9e507cf4fbe6b6bb`) differs
  from it in exactly one further value, `LLAMA_MTMD_FEAT_CACHE_DIR`, which points at the scratch
  cache `/home/chao/feat-cache/scratch-np8-equivalence-20260923`.
* **`--workers` is refused, never clamped**: each roster names its own `sidecar_fragment` in
  `PREPROCESS_ROSTERS`, the driver reads that fragment's `-np` out of `server_args`
  (`_server_slots`), and `--workers` above it exits non-zero with the slot count in the message.
  Every sealed roster keeps the np4 fragment, so no already-sealed composed config hash moves.
* **Roster**: `SLURP-DEVEL-REMAINDER-NP8-EQUIVALENCE-4-V1`
  (`docs/receipts/rosters/slurp-devel-remainder-np8-equivalence-4-v1.json`, raw sha256
  `e7ac3e46a0b4890cb5aa307e12a7d4c47b59c41c98b0e4feef11f0fa17b28e88`, split identity
  `b33dab5f5dcf2cae7d17434e803c39ff61efbdf2e14ce2c1b7ca0b3ff168ec7c`): four ALREADY-PROMOTED
  DEV-2000-ADDED recordings, taken at the 10th / 35th / 65th / 90th percentile positions of the
  duration-sorted promoted pool so the measured per-row wall clock spans the range. 11.90275 audio
  seconds (1.600 / 2.368 / 3.200 / 4.735 s), four distinct scenarios, all four warm in the resident
  cache and served by `DEV-2000-ADDED-promotion.json`. Runtime view
  `configs/dataset/slurp-speech-native-devel-remainder-np8-equivalence-4.json` (canonical
  `86397e8711fdc6b20d70fc4d9abca62a526c8639c29a65563ffd7fd1a4d30ecd`).
* **It opens no new speech identity**: all four rows were already contacted under
  `SAEA-SN-DEV2000-ADDED-PREPROCESS`.
* **What it compares.** After ENCODE into the scratch cache, per row: each chunk's feature payload
  SHA-256 (`sha256(feature_bytes)`, the exact digest `materialize_speech_feature_packet` stores)
  against the `feature_sha256` the resident packet manifest already serves, plus the ordinal count,
  token count and `n_embd`; and the whole legacy cache file against the resident cache entry. The
  report (schema `saea-sidecar-geometry-equivalence-receipt-v1`) carries the verdict
  (`EQUIVALENT` / `NOT EQUIVALENT`), the per-row comparison and the measured per-row wall clock.
* **It promotes nothing, and that is enforced.** A roster carrying an `EquivalenceSpec` may name no
  promotion receipt, must declare a scratch legacy cache and a scratch feature root (never the
  resident ones), must have a sidecar whose `LLAMA_MTMD_FEAT_CACHE_DIR` is that same scratch cache,
  is refused `--promote-only`, refuses to start on a non-empty scratch cache (a stale entry would
  make a cache HIT look like a fresh encode), and reaches neither `_promote_roster` nor
  `_write_promotion_receipt` on any path. The driver exits 4 on `NOT EQUIVALENT`.

```bash
cd /home/chao/saea-worktrees/fable-s3dev   # or the main checkout, at a clean tree
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD:$PWD/src"
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
source ~/.venvs/speechrl/bin/activate

python scripts/slurp_evo_fold_preprocess.py --roster devel-remainder-np8-equivalence-4 --preflight-only
python scripts/slurp_evo_fold_preprocess.py --roster devel-remainder-np8-equivalence-4 --run --workers 4 \
    --output docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-devel-remainder-np8-equivalence-4/equivalence-report.json
```

* **Run id**: `SAEA-SN-DEVEL-REMAINDER-NP8-EQUIVALENCE-4-V1`, attempt `attempt-np8-equivalence-4-v1`.
* **Composed config** `q4km-preprocess-featcache-cpu-sidecar-np8-scratch` /
  `slurp-speech-native-devel-remainder-np8-equivalence-4` / `speech-native-preprocess` /
  `slurp-devel-remainder-np8-equivalence-4-preprocess`, **config hash**
  `bd39d33f520a9d9ae9c8e3b7b882e90c803b3d6614c855ec367268839c82f8c4`, arm `bare-core`, **protocol
  hash** `14132ad08928814adba1021cf6162b2dc02945db5339bba313fa0af82d4226ca` (computed through
  `core.config.compose` / `core.config.protocol_hash`, never hand-typed).
* **Expected counts**: 4 frozen-core contacts at `max_tokens: 1`, 11.90275 speech seconds (declared
  12), 0 packets promoted, 0 promotion receipts written.
* **Expected GPU hours**: **0.0 actually consumed** (`-ngl 0 --no-mmproj-offload`); the declared
  ceiling is `1.0`, the precedent's value. Wall clock: a few minutes, dominated by the sidecar load.
* **Decision rule, stated before it runs**: `EQUIVALENT` on 4 of 4 rows admits `-np 8` for
  preparation 1. Anything else stops the expansion at `-np 4` -- the roster table's
  `sidecar_fragment` for `devel-remainder` moves back to `q4km-preprocess-featcache-cpu-sidecar`,
  which re-pins its composed and protocol hashes and needs a re-registration.

## 3. Preparation 1 of 3 -- speech packet promotion (ENCODE + PROMOTE) (v1 bindings; superseded by section 10)

* **Precedent artifact**: `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/DEV-2000-ADDED-promotion.json`
  (1,000 packets), written by run `SAEA-SN-DEV2000-ADDED-PREPROCESS`.
* **Registered by this change**: roster key `devel-remainder` in `PREPROCESS_ROSTERS`, plus the
  experiment fragment `configs/experiment/slurp-devel-remainder-preprocess.json` (raw sha256
  `197a2720b03916c7131ec0ebdf6a19c1de3581747ca0d88b436792890b42435c`). Composed config
  `q4km-preprocess-featcache-cpu-sidecar-np8` / `slurp-speech-native-devel-remainder` /
  `speech-native-preprocess` / `slurp-devel-remainder-preprocess`, **config hash**
  `6c99858bb643b4c22833ce419e558b73b3875e2a9352120b9354e7d5647e4ba8`, arm `bare-core`, **protocol
  hash** `04102a5e6eb2bcbffb9fcce2496d4beb77d5e7c64fcb8ec7746785a41c47e067`.

```bash
# 1a. zero-contact preflight: D1 media identity for all 6,690 rows + the warm-cache count
python scripts/slurp_evo_fold_preprocess.py --roster devel-remainder --preflight-only

# 1b. ENCODE (6,690 contacts on the CPU-only sidecar, port 8081) + PROMOTE (0 contacts)
python scripts/slurp_evo_fold_preprocess.py --roster devel-remainder --run \
    --workers 8 --promote-workers 8 \
    --output docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-devel-remainder-packets/preprocess-report.json
```

or, as a scheduled task (owner decision 77: each CPU-resident pass is its own task, not one
long-lived process):

```bash
PREP_ROSTER=devel-remainder PREP_WORKERS=8 PREP_PROMOTE_WORKERS=8 \
  PREP_SIDECAR_FRAGMENT=q4km-preprocess-featcache-cpu-sidecar-np8 \
  bash scripts/flights/batch/prep_generic_task_entry.sh
```

* **Run id**: `SAEA-SN-DEVEL-REMAINDER-PREPROCESS`, attempt `attempt-packets-devel-remainder-v1`.
* **Receipt paths**: `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/DEVEL-REMAINDER-promotion.json`
  (schema `saea-speech-packet-promotion-receipt-v1`, 6,690 packets, the sidecar session + stop
  receipt hashes with `forced=false`); the driver's own `saea-slurp-evo-fold-preprocess-receipt-v1`
  report at the `--output` path; the run directory
  `$SPEECHRL_DATA_DIR/runs/SAEA-SN-DEVEL-REMAINDER-PREPROCESS/attempt-packets-devel-remainder-v1/`.
* **Ledger row**: `SAEA-SN-DEVEL-REMAINDER-PREPROCESS` (drafted in `docs/exposure-ledger.md`,
  `consumed = no`).
* **Expected counts**: 6,690 frozen-core contacts at `max_tokens: 1`; 18,978.9523125 speech seconds
  (declared 18,979); 6,690 promoted packets, all new, 0 re-verifications and 0 shared.
* **Expected GPU hours**: **0.0 actually consumed** (`-ngl 0 --no-mmproj-offload`, the GPU stays
  free for the resident serving session); the declared ceiling is `1.0`, the precedent's value.
* **Expected wall clock** -- see section 6. Both bounds are stated because the remainder's rows are
  shorter than R01's (mean 2.837 s against 4.364 s) and the cost has both a per-second and a per-row
  component.
* **Host memory**: the task entry's watchdog stops the pass if available memory falls below 6 GB.
  The host has 43 GB total and about 38 GB available with the GPU session resident.

## 4. Preparation 2 of 3 -- speech query vectors (an encoder contact) (v1 bindings; superseded by section 10)

Modelled one for one on `SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1` and, after it,
`SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1`. Three steps, of which only the middle
one is a contact.

**Step 2a ran here, because it is model-free.** `scripts/build_speech_query_source_inventory.py`
built `$SPEECHRL_DATA_DIR/coordination/slurp-devel-remainder-speech-query-source-inventory-v1.json`
(**sha256 `a7fd59a6dba79aa3c94cae738744daf5324e133f1cd80b476e5a69818d3163ed`**, 6,690 rows, split
identity `e65cd3b1...`, `audio_seconds_total` 18978.952312) from the committed runtime view and
roster receipt: byte hashes plus audio HEADER geometry, no decode, no encoder, no tokenizer, no
network. The command line, for the record:

```bash
python scripts/build_speech_query_source_inventory.py \
    --runtime-view configs/dataset/slurp-speech-native-devel-remainder.json \
    --roster-receipt docs/receipts/rosters/slurp-devel-remainder-v1.json \
    --data-root "$SPEECHRL_DATA_DIR" --source-root "$PWD" \
    --out "$SPEECHRL_DATA_DIR/coordination/slurp-devel-remainder-speech-query-source-inventory-v1.json"
```

**Step 2b is the contact.** Protocol
`configs/preparation/slurp-devel-remainder-speech-query-encoding-protocol-v1.json` (raw sha256
`66a86ec225881b2b818c3855c74aaa7b824c037788dcd4a6b25f0b84a8790360`) is the DEV-2000-ADDED protocol
field for field except the seven roster-bound values (`cache_relpath`, `expected_unique_spans`,
`isolation`, `output_relpath`, `query_rows_relpath`, `roster_sha256`, `sources`) and **`cpu_workers`,
which is 8 rather than 4** -- decision 107's "more workers", still inside the standing cap of 8 CPU
workers beside a GPU campaign. Its `sources` pins the step-2a inventory from the start, so the
two-correction sequence the DEV-2000-ADDED protocol had to record is not expected. The runtime
config cannot be committed (`core.speech_preparation_runtime.main` refuses unless its `study_head`
equals the HEAD of the clean checkout the launch runs from), so it is minted:

```bash
PREP_SET=devel-remainder bash scripts/flights/batch/prep_generic_encode_task_entry.sh
# PREP_DRY=1 rehearses: it mints nothing, contacts nothing, and prints the two mutating lines.
```

That entry refuses a dirty tree, refuses to start while a GPU flight is running (the encoder takes
the card), mints the runtime config, runs step 2b, and then runs the two zero-contact steps below
and prints every output hash.

* **Run id**: `SAEA-SLURP-DEVEL-REMAINDER-SPEECH-QUERY-ENCODING-V1`, attempt `encode-v1`.
* **Receipt paths**: `preparation-runs/SAEA-SLURP-DEVEL-REMAINDER-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json`
  (schema `saea-speech-query-preparation-receipt-v1`) beside `events.jsonl` / `monitor.jsonl`;
  outputs `prepared/SAEA-SLURP-DEVEL-REMAINDER-SPEECH-QUERY-ENCODING-V1/{index.json,queries.jsonl}`;
  alias receipt `prepared/SAEA-SLURP-DEVEL-REMAINDER-ALIAS-V1/query-dimension-alias.json`; alias
  export `vectors/slurp-devel-remainder-v1/query-vectors-speech-segments.jsonl`.
* **Ledger row**: `SAEA-SLURP-DEVEL-REMAINDER-SPEECH-QUERY-ENCODING-V1` (drafted, `consumed = no`).
  The zero-contact `content` -> `intent-boundary` alias (step 2c) rides under the same row, as the
  DEV-2000-ADDED and R01 aliases did.
* **Expected counts**: **6,690 encoder contacts** (one per recording; 0 of these rows are covered by
  any existing query-vector file -- both committed SLURP query-vector files are the 1,080-row TRAIN
  Fold A query side and the 800-row R01 side, neither of which can contain a devel recording) and
  18,978.9523125 speech seconds (declared 18,979). Zero frozen-core contacts, zero answers, zero
  scoring.
* **Expected GPU hours**: about **0.48** -- the DEV-2000-ADDED receipt records `elapsed_seconds
  273.14` for 1,000 contacts / 2,983.527 speech seconds, so 273.14 x (18978.95 / 2983.527) = 1,738 s
  = 29 minutes (row-scaled: 1,827 s = 30.5 minutes; the two agree here because the encoder's cost is
  dominated by the forward, not the file). The declared ceiling is `2.0`, the precedent's value.

## 5. Preparation 3 of 3 -- the content-dimension derivative (model-free) (v1 bindings; superseded by section 10)

Exactly R01's step 3: a zero-contact flatten of preparation 2's alias export into the `content`
dimension, every float byte-identical to the parent's single segment vector.

```bash
python scripts/build_slurp_query_content_derivative.py \
    --source-relpath vectors/slurp-devel-remainder-v1/query-vectors-speech-segments.jsonl \
    --source-sha256 SHA256_PRINTED_BY_STEP_2C \
    --out-dir vectors/slurp-devel-remainder-v1 \
    --out-name query-vectors-speech-content-v1.jsonl \
    --ledger-row SAEA-SLURP-DEVEL-REMAINDER-QUERY-VECTOR-EXPORT-V1
```

`prep_generic_encode_task_entry.sh` runs it as step D with the hash step 2c printed, so the
`SHA256_PRINTED_BY_STEP_2C` placeholder is never typed by hand.

* **Run id**: `SAEA-SLURP-DEVEL-REMAINDER-QUERY-VECTOR-EXPORT-V1`, profile `model-free-check`.
* **Receipt paths**: `vectors/slurp-devel-remainder-v1/query-vectors-speech-content-v1.jsonl` plus
  its sibling `...provenance.json` (schema `saea-slurp-exemplar-query-vectors-provenance-v1`,
  `parent_relpath` = the segment file, `row_count` 6,690, `source_dimension` `intent-boundary`,
  `target_dimension` `content`).
* **Ledger row**: `SAEA-SLURP-DEVEL-REMAINDER-QUERY-VECTOR-EXPORT-V1` (drafted, `consumed = no`).
* **Expected counts**: 6,690 rows; **0 model / encoder / tokenizer / network contacts, 0 speech
  seconds, 0 GPU hours**.

## 6. Order, and the throughput projection (v1; superseded by section 10)

| # | Step | Contacts | Depends on |
| --- | --- | ---: | --- |
| 0 | np8 geometry equivalence (`...-NP8-EQUIVALENCE-4-V1`) | 4 frozen-core | the committed 4-row roster + view |
| 1 | ENCODE + PROMOTE packets (`SAEA-SN-DEVEL-REMAINDER-PREPROCESS`) | 6,690 frozen-core | step 0 returning EQUIVALENT |
| 2a | Speech-query source inventory (model-free) | 0 | **done** (sha256 `a7fd59a6...`) |
| 2b | Speech-query encoding (`...-SPEECH-QUERY-ENCODING-V1`) | 6,690 encoder | 2a; run after step 1 closes so it never competes for CPU custody, and never while a GPU flight runs |
| 2c | Segment dimension alias (model-free) | 0 | 2b |
| 3 | Content-dimension derivative (`...-QUERY-VECTOR-EXPORT-V1`) | 0 | 2c |

**Throughput projection for step 1, from the one measurement we have.** The R01 recovery ENCODE ran
**800 rows / 3,491.426 audio seconds in 6,268 s at `--workers 4`** (0.12763 rows/s; 0.55702 audio
seconds per wall second). Scaled to the remainder's 6,690 rows / 18,978.95 audio seconds:

| Basis | at 4 workers (`-np 4`) | at 8 workers (`-np 8`), IF throughput scales with slots |
| --- | ---: | ---: |
| audio-second-scaled | 34,072 s = **9.46 h** | 17,036 s = **4.73 h** |
| row-scaled | 52,416 s = **14.56 h** | 26,208 s = **7.28 h** |

The truth is between the two bounds: the remainder's rows are shorter (mean 2.837 s against R01's
4.364 s), so a per-second model under-counts the per-row overhead and a per-row model over-counts the
encoder work. **The np8 column is an assumption, not a measurement**: the 4-row preflight of section
2 measures feature EQUIVALENCE and per-row wall clock, and four rows cannot measure aggregate
throughput scaling. The first honest np8 throughput number is the `encode_rows_per_second` the step-1
report itself records; if it comes back below the 4-worker rate, the slot count is the wrong lever
and the next candidate is CPU-side parallelism (the host has 24 cores and the standing baseline is
about 20 idle / 8 during a campaign).

**Measured here, model-free, for calibration**: the 6,690-row media inventory (header probe +
SHA-256 of 359 MB) took **7.918 s** at 8 workers (845 files/s, 43.3 MiB/s), the 6,690 FNV-1a cache
keys took **5.129 s** (1,304 files/s), and the driver's own `--preflight-only` (which re-hashes every
media file and runs the D1 media-identity gate over all 6,690 rows) took **83.6 s**. None of the
model-free preparation work is a bottleneck.

## 7. What the owner still has to decide, before anything here is read as evidence

**Deviation REM-D1 (recorded in the roster receipt, not buried here).** "Everything that is not
DEV-1000 or DEV-2000-ADDED" necessarily contains the **60 FINAL60 recordings**
(`docs/receipts/probe-samples/FINAL60.json`, whose own `split_role` is **`reserved-final-unread`**,
held back by the DEV ladder on 2026-08-23) and the **60 historic probe-60 recordings**
(`configs/probes/g0-binding/pslu-sample-devel-n60.json`). The two sets share no recording and no
utterance. They are neither dropped nor quietly consumed here: they are in the roster, counted in
its `reserved_sets_inside_the_remainder` block (60 + 60 recordings; 254 and 249 remainder recordings
respectively belong to their utterances), and the owner is asked to either **acknowledge that
decision 107 releases the FINAL60 reservation** or **carve those 120 recordings out** before the
remainder is read. Carving them out is a one-line change to the generator's exclusion set and a fresh
receipt; it cannot be done after the rows have been flown.

**Answered on 2026-09-23 (provisional decision 109): carve them out.** See section 10. The generator
grew `--exclude-receipt` and `--version`, the 120 recordings left the roster, and the deviation is
re-stated in the V2 receipt as the *utterance-level residue* the carve-out could not remove.

**Deviation REM-D2.** 1,719 of the 1,839 remainder utterances already have a recording in a sealed
half; only **120** remainder utterances were never read before (and those 120 are exactly the FINAL60
and probe-60 utterances). One utterance contributes up to 59 remainder recordings. Every paired
analysis must cluster by `utterance_id`, and a remainder result and a DEV-1000 / DEV-2000-ADDED
result are **not** independent utterance samples. The expansion buys far-field and speaker variation
on utterances the system has largely already seen, not 6,690 fresh utterances -- that is what the
devel split contains, and the plan should not be read as if it were otherwise.

**Deviation REM-D3.** No equal-per-scenario allocation is possible: the remainder is whatever the two
sealed halves left (`play` 997, `calendar` 864, `qa` 592 ... `takeaway` 147). Report every
DEVEL-REMAINDER verdict under both natural-mixture and equal-stratum weighting, per the 2026-09-03
reporting rule.

**Text contamination, measured digest-only against the TRAIN construction pool** (method carried
from `scripts/build_slurp_evo_decontamination.py`; only counts and digest-set hashes leave the
generator): the remainder's 1,839 utterances carry **3** exact sentence matches and **210**
utterances sharing a TRAIN 6-gram, against the sealed DEV-1000 half's **1** and **111** of 1,000
under the identical method -- the same rate, not a new exposure.

**The four ledger rows are DRAFTS.** Each carries `consumed = no` and the status "REGISTERED (draft,
root countersignature pending)"; each still needs root's countersignature at a clean tree before the
corresponding step may run.

## 8. What this document does not authorise

No contact of any kind, no readiness flip, no cell registration, no campaign-plan entry, no queue
append, and no scoring or answer read. It does not admit `-np 8`: section 2's preflight does, and
only if it returns `EQUIVALENT`. It registers no consuming cell -- what a cell would bind
(the promotion receipt, the two vector files, the runtime view, the utterance clustering of REM-D2
and the dual weighting of REM-D3) enters only through that cell's own registration.

## Stage-3 algorithm label (owner decision 101)

**`none`** -- the four steps registered here are model-free / preparation steps and carry no
training-free RL operator. The label lives here as prose rather than in the experiment fragments
because neither fragment is a Stage-3 cell:
`scripts/checks/stage3_algorithm_label_check.py` puts a fragment in scope only through a `stage3`
token in its stem or `experiment_id` or a reference to one of the two Stage-3 specs, and none of
`slurp-devel-remainder-preprocess.json`, `slurp-devel-remainder-preprocess-v2.json` (the v2
successor, section 10) or `slurp-devel-remainder-np8-equivalence-4-preprocess.json` carries any of
those. The gate confirms it: 8 Stage-3 cells of 446 experiment fragments (445 before the v2
fragment), unchanged by this registration.

## 9. The files this plan registers (v1; section 10 lists the v2 files)

| File | Raw sha256 | What it is |
| --- | --- | --- |
| `docs/receipts/rosters/slurp-devel-remainder-v1.json` | `83f618bd…` | the 6,690-row take-all roster |
| `configs/dataset/slurp-speech-native-devel-remainder.json` | `192a2144…` | its label-free runtime view |
| `docs/receipts/rosters/slurp-devel-remainder-np8-equivalence-4-v1.json` | `e7ac3e46…` | the 4-row np8 preflight roster |
| `configs/dataset/slurp-speech-native-devel-remainder-np8-equivalence-4.json` | `5017cb56…` | its runtime view |
| `configs/model/q4km-preprocess-featcache-cpu-sidecar-np8.json` | `3bf04cfb…` | the np4 sidecar with `-np 8` |
| `configs/model/q4km-preprocess-featcache-cpu-sidecar-np8-scratch.json` | `57db716f…` | the same, pointed at the scratch cache |
| `configs/experiment/slurp-devel-remainder-preprocess.json` | `197a2720…` | the packet-promotion cell |
| `configs/experiment/slurp-devel-remainder-np8-equivalence-4-preprocess.json` | `f492badb…` | the equivalence preflight cell |
| `configs/preparation/slurp-devel-remainder-speech-query-encoding-protocol-v1.json` | `66a86ec2…` | the step-2b protocol |
| `configs/preparation/slurp-devel-remainder-query-alias-v1.json` | `b9fc487e…` | the step-2c alias template |
| `scripts/build_slurp_devel_remainder_roster.py` | `f37a18eb…` | the roster generator |
| `scripts/build_slurp_runtime_view.py` | `989fd2b5…` | the roster-parameterised runtime-view builder |
| `scripts/build_slurp_np8_equivalence_roster.py` | `64344e4b…` | the 4-row preflight roster generator |
| `scripts/flights/batch/prep_generic_steps.py` | `0b1187d7…` | the generic runbook helper steps |
| `scripts/flights/batch/prep_generic_task_entry.sh` | `393e179e…` | the generic packet-promotion task entry |
| `scripts/flights/batch/prep_generic_encode_task_entry.sh` | `91d83295…` | the generic query-encoding task entry |
| `docs/checks/…/2026-09-23-slurp-devel-remainder-roster/disjointness.json` | `1f0d8773…` | the roster's disjointness proof |
| `docs/checks/…/2026-09-23-slurp-devel-remainder-packets/media-inventory.json` | `b82040cc…` | the media inventory + cache warmth |
| `docs/checks/…/2026-09-23-slurp-devel-remainder-packets/packet-preparation-plan.json` | `6a90ea99…` | what remains for the packets |

Tests, after the section-10 carve-out: `tests/unit/test_slurp_devel_remainder_roster.py` (33,
was 23), `tests/unit/test_devel_remainder_preprocess_rosters.py` (25),
`tests/unit/test_devel_remainder_preparation_configs.py` (24, was 23), and
`tests/unit/test_e33_preprocess_rosters.py` (13), whose exact-set assertion over
`PREPROCESS_ROSTERS` names the two keys this plan added. The three DEVEL-REMAINDER modules now
assert the V2 artifacts and keep a short section proving V1 is still committed, intact and
correctly superseded.

## 10. v2 carve-out (provisional decision 109)

**Ruling, 2026-09-23 (coordinator, provisional decision 109).** The remainder must not spend the
FINAL60 reservation and must stay contact-fresh. Both reserved sets are therefore excluded and the
roster is re-frozen as a **new version**; the v1 receipt is kept committed as the superseded parent
and is never rewritten.

### 10.1 What was excluded, and the proof that it is exactly 120 recordings

| Set | Receipt | Recordings | Utterances | Already in a sealed half |
| --- | --- | ---: | ---: | ---: |
| FINAL60 (`split_role` `reserved-final-unread`, held back 2026-08-23) | `docs/receipts/probe-samples/FINAL60.json` (`630d6e25…`) | 60 | 60 | 0 |
| historic probe-60 (already contacted by early probes; the 60 warm legacy-cache rows) | `configs/probes/g0-binding/pslu-sample-devel-n60.json` (`782609ac…`) | 60 | 60 | 0 |
| **union** | | **120** | **120** | **0** |

The two sets share **0 recordings and 0 utterances** (`carved_out_reserved_sets.
pairwise_shared_recordings` / `…_utterances`), so the union is exactly 60 + 60 = 120. SHA-256 over
the sorted excluded sample-id list:
`30ca991cc7957d5e6d18cbe7d8a303f174bec83d73bcd36315ce2bbbcd50767c`.

### 10.2 The v2 roster, number for number against v1

| | v1 (`SLURP-DEVEL-REMAINDER-V1`) | **v2 (`SLURP-DEVEL-REMAINDER-V2`)** | delta |
| --- | ---: | ---: | ---: |
| recordings | 6,690 | **6,570** | -120 |
| distinct utterances | 1,839 | **1,827** | -12 |
| audio seconds | 18,978.9523125 | **18,611.584875** | -367.3674375 |
| declared ceiling | 18,979 | **18,612** | -367 |
| mean / min / max seconds | 2.837 / 0.512 / 13.166 | **2.833 / 0.512 / 13.166** | |
| headset / far-field | 3,235 / 3,455 | **3,176 / 3,394** | -59 / -61 |
| media bytes | 359,107,433 | **352,145,084** | -6,962,349 |
| excluded candidates | 2,000 | **2,120** | +120 |
| warm in the legacy feature cache | 60 | **0** | -60 |
| already promoted under the resident root | 0 | **0** | 0 |
| split identity hash | `e65cd3b1…` | **`f8af142b…`** | |

Only **12** utterances left with their recordings: those whose *only* devel recording outside the
two sealed halves was a reserved one. The seed is unchanged (`20260923`), the draw is still the
take-all freeze through `core.roster.freeze_roster`, and `roster_role` / `split_role` /
`stratum_withheld_per_item` / `target_gold_opened_before_receipt` are unchanged.

**Completeness still holds, with a fourth part.** DEV-1000 (1,000) + DEV-2000-ADDED (1,000) +
CARVED-OUT (120) + DEVEL-REMAINDER (6,570) = **8,690** = the complete devel split, pairwise
disjoint, proven id by id in the receipt's `completeness` block. Nothing is lost; the 120
recordings are named and set aside.

**Disjointness.** Every `shared_with_*` line of the V2 `disjointness_proof` is 0, including the
three new ones: `shared_with_carved_out_final60_recordings`,
`shared_with_carved_out_historic_probe60_recordings` and
`shared_with_any_carved_out_recording`.

### 10.3 The residue a recording-level carve-out cannot remove

Devel carries several recordings of one utterance, so excluding a *recording* does not exclude its
*sentence*. **108 of the 120 carved-out utterances still have sibling recordings on the v2 roster --
383 recordings in total** (194 of the FINAL60 utterances, 189 of the probe-60 utterances). Reading
them exposes the same sentence and the same gold as the reserved recordings would, through a
different microphone. That is why the v2 text-contamination profile against the TRAIN construction
pool is unchanged from v1 (**3** exact sentence matches, **210** utterances sharing a TRAIN 6-gram,
now over 1,827 utterances instead of 1,839).

This is recorded as deviation **REM-D1** in the V2 receipt, with the owner action: *decide whether
the utterance-level residue also has to go (a further 383 recordings and a third version of this
roster), or accept that the reservation is enforced at recording granularity only.* **Open for the
coordinator; nothing here assumes an answer.**

### 10.4 The revised throughput projection

Same measurement as section 6 (the R01 recovery ENCODE: 800 rows / 3,491.426 audio seconds in
6,268 s at `--workers 4`), rescaled to 6,570 rows / 18,611.584875 audio seconds:

| Basis | at 4 workers (`-np 4`) | at 8 workers (`-np 8`), IF throughput scales with slots |
| --- | ---: | ---: |
| audio-second-scaled | 33,413 s = **9.28 h** (v1: 9.46 h) | 16,706 s = **4.64 h** (v1: 4.73 h) |
| row-scaled | 51,476 s = **14.30 h** (v1: 14.56 h) | 25,738 s = **7.15 h** (v1: 7.28 h) |

The np8 column is still an assumption, not a measurement; the 4-row equivalence preflight of
section 2 measures feature equivalence and per-row wall clock, not aggregate scaling. Step 2b
(query encoding) rescales the DEV-2000-ADDED receipt's 273.14 s / 2,983.527 speech seconds the same
way: **1,704 s = 28.4 minutes = 0.47 GPU hours** audio-scaled (1,795 s = 29.9 min row-scaled); the
declared ceiling stays the precedent's `2.0`.

### 10.5 The v2 files, and what they replace

| v2 file | Raw sha256 | Replaces |
| --- | --- | --- |
| `docs/receipts/rosters/slurp-devel-remainder-v2.json` | `b695a6bd…` | `…-v1.json` (`83f618bd…`) |
| `configs/dataset/slurp-speech-native-devel-remainder-v2.json` | `51ea5ad6…` (canonical `72a8d829…`) | `…-devel-remainder.json` (`192a2144…`, canonical `5ecda759…`) |
| `configs/experiment/slurp-devel-remainder-preprocess-v2.json` | `af1001a9…` | `…-preprocess.json` (`197a2720…`) |
| `configs/preparation/slurp-devel-remainder-speech-query-encoding-protocol-v2.json` | `2e646bd2…` | `…-protocol-v1.json` (`66a86ec2…`) |
| `configs/preparation/slurp-devel-remainder-query-alias-v2.json` | `db7f948a…` | `…-alias-v1.json` (`b9fc487e…`) |
| `docs/checks/…/2026-09-23-slurp-devel-remainder-v2-roster/disjointness.json` | `640c4b3b…` | `…-roster/disjointness.json` |
| `docs/checks/…/2026-09-23-slurp-devel-remainder-v2-packets/media-inventory.json` | `9c5741e5…` | `…-packets/media-inventory.json` |
| `docs/checks/…/2026-09-23-slurp-devel-remainder-v2-packets/packet-preparation-plan.json` | `4d9885d0…` | `…-packets/packet-preparation-plan.json` |
| `$SPEECHRL_DATA_DIR/coordination/slurp-devel-remainder-speech-query-source-inventory-v2.json` | `d8ca6915…` | `…-v1.json` (`a7fd59a6…`) -- outside Git, model-free, 6,570 rows |

Re-pointed in place (the run ids, attempts, vector and coordination directories are **unchanged**,
because no contact has been made under any of them): `PREPROCESS_ROSTERS["devel-remainder"]` in
`scripts/slurp_evo_fold_preprocess.py` (now 6,570 calls / 18,612 declared speech seconds on the v2
fragments), `PREPARATION_SETS["devel-remainder"]` in `scripts/flights/batch/prep_generic_steps.py`
(v2 protocol / alias / roster / dataset / inventory, `rows` 6,570, `planned_speech_audio_seconds`
18,612, v2 split identity), and the four DRAFT exposure-ledger rows.

**Re-pinned hashes for preparation 1.** Composed config
`q4km-preprocess-featcache-cpu-sidecar-np8` / `slurp-speech-native-devel-remainder-v2` /
`speech-native-preprocess` / `slurp-devel-remainder-preprocess-v2`, **config hash**
`4526c012b94a91679b9e28502d3939a3a4a5e204d2258fce8152fadb132b4be3` (v1:
`6c99858b…`), arm `bare-core`, **protocol hash**
`e01218edf4467cdf5fbf14a2069b619e4b348e324e787ad8b06ade49a00e4a65` (v1: `04102a5e…`). The np8
geometry-equivalence preflight of section 2 is **unaffected**: its roster is drawn from
DEV-2000-ADDED, and its config hash `bd39d33f…` and protocol hash `14132ad0…` were re-computed here
and are unchanged.

### 10.6 How to reproduce the v2 freeze

```bash
python scripts/build_slurp_devel_remainder_roster.py --version 2 \
    --exclude-receipt docs/receipts/probe-samples/FINAL60.json \
    --exclude-receipt configs/probes/g0-binding/pslu-sample-devel-n60.json --write

python scripts/build_slurp_runtime_view.py \
    --roster-receipt docs/receipts/rosters/slurp-devel-remainder-v2.json \
    --output configs/dataset/slurp-speech-native-devel-remainder-v2.json \
    --checks-dir docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-devel-remainder-v2-packets \
    --workers 8 --write

python scripts/build_speech_query_source_inventory.py \
    --runtime-view configs/dataset/slurp-speech-native-devel-remainder-v2.json \
    --roster-receipt docs/receipts/rosters/slurp-devel-remainder-v2.json \
    --data-root "$SPEECHRL_DATA_DIR" --source-root "$PWD" \
    --out "$SPEECHRL_DATA_DIR/coordination/slurp-devel-remainder-speech-query-source-inventory-v2.json"
```

`--version 1` with no `--exclude-receipt` still reproduces the v1 receipt and its disjointness
document **byte for byte** -- verified in this worktree by rebuilding both and comparing bytes --
so the generalised generator did not silently change the parent.

### 10.7 What section 10 does not do

It does not rewrite the v1 receipt (no `superseded_by` key was grafted onto it: the v1 media
inventory, the v1 protocol, the v1 ledger prose and this note all pin its file hash, and every one
of those pins would break). It authorises no contact, flips no readiness state, mints no decision
receipt and countersigns no ledger row. It does not admit `-np 8`; section 2's preflight still does,
and only on `EQUIVALENT`. Decision 109 is recorded here as **provisional**: it is the coordinator's
ruling, and the owner's own decision log entry is still owed.
