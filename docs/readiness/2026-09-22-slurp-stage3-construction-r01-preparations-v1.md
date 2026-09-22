# SLURP-STAGE3-CONSTRUCTION-R01 preparation plan, v1

Stage-3 item S3-1 (`docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md`). This
document states what cell ROLL-1 (`configs/experiment/slurp-native-stage3-rollout-r01-v1.json`,
package `docs/readiness/2026-09-22-slurp-stage3-rollout-r01-v1/`) needs before it can fly, and how
each of the 18 `PENDING_STAGE3_CONSTRUCTION_R01_*` entries of the `stage3_pending_placeholders`
block of `configs/baseline/slurp-native-stage3-rollout-baseline-v1.json` is filled. It registers no
cell, authorises no contact and flips no readiness state. Every number below was measured
model-free in worktree `/home/chao/saea-worktrees/fable-s3p` (branch `fable/s3p`) at study commit
`803c1ca8`: zero model, tokenizer, encoder, embedder, scorer, GPU and network contacts, and no
audio sample was decoded.

Precedent throughout: the DEV-2000-ADDED preparation chain of cell B6
(`docs/readiness/2026-09-21-slurp-b6-dev2000-added-preparation-plan-v1.md`).

## 0. The roster in one paragraph

`SLURP-STAGE3-CONSTRUCTION-R01` (`docs/receipts/rosters/slurp-stage3-construction-r01.json`, raw
sha256 `fdb6521a0863b5f11f7ccea9fba5a1e598d65c5eb05b13a68d1198d5e01ba5f0`): 800 construction-pool
SLURP TRAIN recordings, 18 scenario strata of 44 or 45, farthest-point draw seeded 20260922,
`roster_role: construction`, `split_role: discovery`, split identity hash
`2ece5e51ff781fdec89bef8e7448d8ba88249030d3c8a6478dba5e7c1e621dac`. Runtime view
`configs/dataset/slurp-speech-native-stage3-construction-r01.json` (raw sha256
`b3c1239d92ea95c03ec371cc010db47c8f0ea4312a8e3e38d4efc4dbd6dbf0b5`, canonical
`runtime_view_sha256` `d3503d5861943b975b213ec2804e094e084e63206f31cb0b1b5715e815338bdd`).
**Audio: 3,491.426125 seconds total** (58.19 minutes; 800 recordings, mean 4.364 s, min 1.216 s,
max 15.294 s), read from the roster receipt's `items[].audio_seconds` and confirmed against the
runtime view's `audio_seconds_total`. The declared ceiling everywhere below is `3492`
(`ceil(3491.426125)`), the form the DEV-2000-ADDED plan used.

**Re-pinned 2026-09-22 after decision 93 (the D1 media supplement pinned the dataset fragment; runtime view, fragment raw sha, composed config and protocol hashes moved; the preprocess ledger row was re-pinned in the same commit).**

## 1. Coverage finding: how many R01 rows already have featcache packets

**8 of 800 rows are already promoted; 792 need ENCODE.**

Method (id-level only; no packet byte, no audio sample and no `.feat` file was read): every
`saea-speech-packet-promotion-receipt-v1` document under the resident packet root
`/home/chao/feat-cache/slurp-q4km-packets-04ccc72a` was parsed for its `packets[].packet_id` set and
intersected with the 800 roster `packet_id`s (`sample_id` with `:` replaced by `/`); the result was
then confirmed against the on-disk leaf directories `slurp/train/<utterance>/<recording>` under the
same root.

| Promotion receipt inspected | packets | R01 rows covered |
| --- | ---: | ---: |
| `DEV-100-promotion.json` | 100 | 0 |
| `DEV-500-promotion.json` | 500 | 0 |
| `DEV-1000-promotion.json` | 1,000 | 0 |
| `DEV-2000-ADDED-promotion.json` | 1,000 | 0 |
| `EVO-FOLD-A-V2-promotion.json` | 1,080 | 0 |
| `EVO-FOLD-B-V2-promotion.json` | 1,080 | 0 |
| `EVO-FOLDS-V2-promotion.json` (union of the two folds) | 2,160 | 0 |
| `SLURP-KNOWLEDGE63-promotion.json` | 63 | 0 |
| `KEY18` / `OPT-B18` / `ENG-GATE8-promotion.json` | 18 / 18 / 8 | 0 |
| `TRAIN90-promotion.json` | 90 | 2 |
| `GATE18-promotion.json` | 18 | 1 (also in TRAIN90) |
| `OPT-A36-promotion.json` | 36 | 1 (also in TRAIN90) |
| `GATE-C36-promotion.json` | 36 | 2 |
| `EFFECT-C108-promotion.json` | 108 | 2 |
| `EVIDENCE-E108-promotion.json` | 108 | 1 |
| `FACTOR-D108-promotion.json` | 108 | 1 |
| **union of all 18 receipts** | **4,673** | **8** |
| on-disk `slurp/train/**` leaf packet directories under the same root | 2,673 | 8 (the same 8) |

This is exactly what the S3-1 draw predicts: `scripts/build_slurp_stage3_construction_roster.py`
excluded TRAIN Fold A, TRAIN Fold B, DEV-1000, DEV-2000 and DEV-2000-ADDED, so the four large
rosters contribute nothing, while the six small August engineering rosters (TRAIN90 and the
18/36/108-row gate, option, effect, evidence and factor sets) were never part of that exclusion
list and therefore overlap the pool by 8 recordings.

**Consequence for preparation 1.** The ENCODE step still contacts **all 800 rows**:
`scripts/slurp_evo_fold_preprocess.py` drives one contact per roster row and does not skip warm rows
(the legacy feature-cache key is the FNV-1a hash of the media bytes alone, so a warm row is cheap
but still a contact). The PROMOTE step is additive and refuse-on-conflict by construction
(`core.model.speech_features.materialize_speech_feature_packet`): those 8 packet ids are re-verified
byte for byte against what the resident root already serves and are **never rewritten**; a mismatch
raises before anything is written. The driver's `--preflight-only` mode prints the
`legacy cache entries warm` count for the roster; that count is the model-free way to learn how many
of the 792 are already warm in `/home/chao/feat-cache/slurp-q4km` before the sidecar starts, and it
was deliberately **not** measured here because it requires hashing every media file's bytes.

## 2. Preparation 1 of 3 -- speech packet promotion (ENCODE + PROMOTE)

* **Precedent artifact**: `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/DEV-2000-ADDED-promotion.json`
  (1,000 packets), written by run `SAEA-SN-DEV2000-ADDED-PREPROCESS`, package
  `docs/readiness/2026-09-21-slurp-dev2000-added-preprocess-v1/`.
* **Producing command (precedent)**: `python scripts/slurp_evo_fold_preprocess.py --roster dev2000-added --run`.
* **Registered for R01 by this change**: roster key `stage3-construction-r01` in that script's
  `PREPROCESS_ROSTERS` table, plus the experiment fragment
  `configs/experiment/slurp-stage3-construction-r01-preprocess.json` (raw sha256
  `0e6c22eb5c45d19ac3da7b19cf7823e4a9d5c91cfce6b25b7f861dea8c37b7de`). Composed config
  `q4km-preprocess-featcache-cpu-sidecar` / `slurp-speech-native-stage3-construction-r01` /
  `speech-native-preprocess` / `slurp-stage3-construction-r01-preprocess`, **config hash**
  `aa1806f36afd529fbcede5d0715f41fabfdb9cbe125cfd752cc9c6e6209b7057`, arm `bare-core`, **protocol
  hash** `d3d3ccd4c1580745a7e0e8bf148defac1ac2d4a27698b84e3e27e6b2099c4725` (computed here through
  `core.config.compose` / `core.config.protocol_hash`, never hand-typed).

Command line to run (not run by this package; it is a tool contact and needs its ledger row
countersigned first):

```bash
cd /home/chao/saea-worktrees/fable-s3p   # or the main checkout, at a clean tree
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD:$PWD/src"
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
source ~/.venvs/speechrl/bin/activate

# 1a. zero-contact preflight: D1 media identity for all 800 rows + the warm-cache count
python scripts/slurp_evo_fold_preprocess.py --roster stage3-construction-r01 --preflight-only

# 1b. ENCODE (800 contacts on the CPU-only sidecar, port 8081) + PROMOTE (0 contacts)
python scripts/slurp_evo_fold_preprocess.py --roster stage3-construction-r01 --run \
    --workers 4 --promote-workers 8 \
    --output docs/checks/speech-aware-evidence-acquisition/2026-09-22-slurp-stage3-construction-r01-packets/preprocess-report.json
```

* **Run id**: `SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS`, attempt
  `attempt-packets-stage3-construction-r01-v1`.
* **Receipt paths**: `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/STAGE3-CONSTRUCTION-R01-promotion.json`
  (schema `saea-speech-packet-promotion-receipt-v1`, 800 packets, `dataset_runtime_view_sha256`
  `1a4d0d62...`, the sidecar session + stop receipt hashes with `forced=false`); the driver's own
  `saea-slurp-evo-fold-preprocess-receipt-v1` report at the `--output` path above; the run directory
  `$SPEECHRL_DATA_DIR/runs/SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS/attempt-packets-stage3-construction-r01-v1/`.
* **Ledger row**: `SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS` (drafted in `docs/exposure-ledger.md`,
  `consumed = no`).
* **Expected counts**: 800 frozen-core contacts at `max_tokens: 1`; 3,491.426125 speech seconds
  (declared 3,492); 800 promoted packets of which 8 are re-verifications and 792 are new.
* **Expected GPU hours**: **0.0 actually consumed** -- the sidecar runs `-ngl 0
  --no-mmproj-offload` and leaves the GPU free for the resident serving session. The declared plan
  ceiling is `1.0`, the precedent's value. Expected **wall clock about 75 minutes**: the
  DEV-2000-ADDED ENCODE window ran 2026-09-21T16:44:20Z to 17:48:01Z = 63.7 minutes for 2,983.527
  audio seconds, and encoding cost tracks audio length, so 63.7 x (3491.426 / 2983.527) = 74.5
  minutes at the same `--workers 4`.
* **ROLL-1 placeholders filled**: `speech_packet_promotion_receipt` and
  `speech_packet_promotion_receipt_sha256`.

## 3. Preparation 2 of 3 -- intent-boundary speech query vectors (an encoder contact)

* **Precedent artifacts**: `vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl`
  (1,080 rows, sha256 `e7a5b226...`, the pin cell PLAN's `intent-boundaries` Perception
  `query_source` carries) and its DEV-2000-ADDED sibling
  `vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl` (1,000 rows, sha256
  `e2a5fd04...`). Ledger rows `SAEA-SLURP-TFRL-FOLD-A-SPEECH-QUERY-ENCODING-V1` and
  `SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1`.
* **Producing commands (precedent)**: three steps, of which only the middle one is a contact.
  1. `scripts/build_speech_query_source_inventory.py` -- model-free
     `saea-speech-query-source-inventory-v1` (byte hashes plus audio HEADER geometry, no decode).
  2. `python -m speech_aware_evidence_acquisition.core.speech_preparation_runtime --config <runtime
     config> --config-sha256 <sha> --data-root <root> --source-root <checkout>` with a
     `saea-speech-query-encoding-protocol-v1` protocol -- the frozen Omni-Embed-Nemotron-3B
     retrieval tool, prompt `query: `, dimension 2048, one contact per recording.
  3. `python -m speech_aware_evidence_acquisition.core.preparation_vectors --config <alias config>
     --config-sha256 <sha> --repo-root <checkout> --data-root <root>` -- the zero-contact
     `saea-sealed-segment-vector-dimension-alias-v1` rename `content` -> `intent-boundary`.

Command lines to run for R01 (none of them run by this package):

```bash
cd /home/chao/saea-worktrees/fable-s3p     # steps 2a/2c may run from any clean checkout
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD:$PWD/src"
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
source ~/.venvs/speechrl/bin/activate

# 2a. MODEL-FREE source inventory (prints the sha256 to pin under protocol.sources.sha256)
python scripts/build_speech_query_source_inventory.py \
    --runtime-view configs/dataset/slurp-speech-native-stage3-construction-r01.json \
    --roster-receipt docs/receipts/rosters/slurp-stage3-construction-r01.json \
    --data-root "$SPEECHRL_DATA_DIR" \
    --source-root "$PWD" \
    --out "$SPEECHRL_DATA_DIR/coordination/slurp-stage3-construction-r01-speech-query-source-inventory-v1.json"

# 2b. THE CONTACT: 800 frozen retrieval-encoder forwards.
#     configs/preparation/slurp-stage3-construction-r01-speech-query-encoding-protocol-v1.json is a
#     copy of the DEV-2000-ADDED protocol with expected_unique_spans 800, roster_sha256
#     fdb6521a0863b5f11f7ccea9fba5a1e598d65c5eb05b13a68d1198d5e01ba5f0, the cache/output/query_rows
#     relpaths renamed to this roster, and sources.{path,sha256} taken from step 2a's printed hash.
python -m speech_aware_evidence_acquisition.core.speech_preparation_runtime \
    --config "$SPEECHRL_DATA_DIR/coordination/slurp-stage3-construction-r01-query-encoding-v1/runtime-config-v1.json" \
    --config-sha256 SHA256_OF_THAT_RUNTIME_CONFIG_AS_WRITTEN \
    --data-root "$SPEECHRL_DATA_DIR" \
    --source-root "$PWD"

# 2c. ZERO-CONTACT dimension alias: content -> intent-boundary
python -m speech_aware_evidence_acquisition.core.preparation_vectors \
    --config configs/preparation/slurp-stage3-construction-r01-query-alias-v1.json \
    --config-sha256 SHA256_OF_THAT_ALIAS_CONFIG_AS_WRITTEN \
    --repo-root "$PWD" \
    --data-root "$SPEECHRL_DATA_DIR"
```

The two `SHA256_OF_..._AS_WRITTEN` values cannot be stated here: both configs pin a hash that does
not exist yet (the runtime config pins the step-2a inventory's sha256, the alias config pins step
2b's `queries.jsonl` sha256), so each file is written, hashed and then passed to its own runner --
the same two-correction sequence the DEV-2000-ADDED protocol records in its `correction_note`.

* **Run id**: `SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1`, attempt `encode-v1`.
* **Receipt paths**: `preparation-runs/SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json`
  (schema `saea-speech-query-preparation-receipt-v1`) beside `events.jsonl` / `monitor.jsonl`;
  outputs `prepared/SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1/{index.json,queries.jsonl}`;
  alias receipt `prepared/SAEA-SLURP-STAGE3-CONSTRUCTION-R01-ALIAS-V1/query-dimension-alias.json`;
  alias export `vectors/slurp-stage3-construction-r01-v1/query-vectors-speech-segments.jsonl`.
* **Ledger row**: `SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1` (drafted,
  `consumed = no`). The alias step rides under the same row, as the DEV-2000-ADDED alias did.
* **Expected counts**: **800 encoder contacts** (`logical_encoder_contacts`, one per recording;
  0 of this roster's rows are covered by any existing query-vector file -- see section 4.1) and
  3,491.426125 speech seconds (declared 3,492). Zero frozen-core contacts, zero answers, zero
  scoring.
* **Expected GPU hours**: about **0.09** -- the DEV-2000-ADDED receipt records
  `elapsed_seconds 273.14` for 1,000 contacts / 2,983.527 speech seconds, so
  273.14 x (3491.426 / 2983.527) = 320 s = 5.3 minutes. The declared plan ceiling is `2.0`, the
  precedent's value.
* **ROLL-1 placeholders filled**: the four `knowledge_stores.intent-boundaries.phase_supply.perception.query_source`
  entries (`embedded_signal`, `relpath`, `sha256`, `tool_contact_ledger_row`) and
  `preparation_source_receipts[7]` (the encoding receipt's relpath + sha256).

## 4. Preparation 3 of 3 -- the train-exemplars content query vectors (model-free)

* **Precedent artifacts**: cell PLAN binds `knowledge_stores.train-exemplars.phase_supply.solver.query_source`
  to `vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl` (kind `sealed-vectors`,
  dimension `content`, sha256 `d0f06ed2...`, ledger row
  `SAEA-SLURP-TFRL-FOLD-A-SPEECH-QUERY-ENCODING-V1`), built by
  `scripts/build_slurp_exemplar_pool_assets.py` as a zero-contact flatten of the Fold A **segment**
  vectors. Cell B6 repeats the transform for a fresh roster with the generalised CLI
  `scripts/build_slurp_query_content_derivative.py`, producing
  `vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.jsonl` (sha256 `7d4ebdce...`).

```bash
# 3. ZERO-CONTACT flatten of preparation 2's alias export into the content dimension
python scripts/build_slurp_query_content_derivative.py \
    --source-relpath vectors/slurp-stage3-construction-r01-v1/query-vectors-speech-segments.jsonl \
    --source-sha256 SHA256_PRINTED_BY_STEP_2C \
    --out-dir vectors/slurp-stage3-construction-r01-v1 \
    --out-name query-vectors-speech-content-v1.jsonl \
    --ledger-row SAEA-SLURP-STAGE3-CONSTRUCTION-R01-QUERY-VECTOR-EXPORT-V1
```

* **Run id**: `SAEA-SLURP-STAGE3-CONSTRUCTION-R01-QUERY-VECTOR-EXPORT-V1`.
* **Receipt paths**: `vectors/slurp-stage3-construction-r01-v1/query-vectors-speech-content-v1.jsonl`
  plus its sibling `...provenance.json` (schema
  `saea-slurp-exemplar-query-vectors-provenance-v1`, `execution_profile: model-free-check`,
  `parent_relpath` = the segment file, `transform` = flatten + dimension rename, every float
  byte-identical to the parent).
* **Ledger row**: `SAEA-SLURP-STAGE3-CONSTRUCTION-R01-QUERY-VECTOR-EXPORT-V1` (drafted,
  `consumed = no`, profile `model-free-check`).
* **Expected counts**: 800 rows; **0 model / encoder / tokenizer / network contacts, 0 speech
  seconds, 0 GPU hours**.
* **ROLL-1 placeholders filled**: the four `knowledge_stores.train-exemplars.phase_supply.solver.query_source`
  entries and `preparation_source_receipts[8]`.

### 4.1 Correction to the ROLL-1 placeholder note (measured, not assumed)

The `stage3_pending_placeholders` note for
`knowledge_stores.train-exemplars.phase_supply.solver.query_source.relpath` says this pin "requires
only a MODEL-FREE alias/subset export of the pool-side content vectors already sealed for **every
TRAIN utterance** (`vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl` parent)".
**That is not the case.** Measured here at id level, with no vector component read:

* `vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl` holds **1,080 rows**, and its
  own `...provenance.json` records `row_count: 1080` with
  `parent_relpath: vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl`.
  It is the **TRAIN Fold A query side**, not a pool-wide export covering every TRAIN utterance.
* Its intersection with the 800 R01 `sample_id`s is **0**, as is the Fold A segment file's -- which
  is exactly right, because the S3-1 draw excluded every Fold A recording.

So preparation 3 cannot be a subset of an existing file; it is a derivative of **preparation 2's own
output**, exactly as cell B6's DEV-2000-ADDED content file is a derivative of the DEV-2000-ADDED
segment file. It stays model-free (0 contacts), but it is **sequenced after** preparation 2 rather
than independent of it, and the encoder contacts of preparation 2 are therefore unavoidable. The
placeholder note should be rewritten at re-pin time to say so.

## 5. Order, and the one blocker fixed here

| # | Step | Contacts | Depends on |
| --- | --- | ---: | --- |
| 1 | ENCODE + PROMOTE packets (`SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS`) | 800 frozen-core | the committed roster receipt + runtime view |
| 2a | Speech-query source inventory (model-free) | 0 | the same two files |
| 2b | Speech-query encoding (`...-SPEECH-QUERY-ENCODING-V1`) | 800 encoder | 2a; run after step 1 closes so it never competes for CPU custody |
| 2c | Segment dimension alias (model-free) | 0 | 2b |
| 3 | Content-dimension derivative (`...-QUERY-VECTOR-EXPORT-V1`) | 0 | 2c |
| 4 | Re-pin ROLL-1, build its prepared supply and its fit | 0 by itself | 1, 2, 3 |

Steps 1 and 2b are CPU-resident passes; per owner decision 77 each launches as its own scheduled
task rather than as one long-lived process, and the resident decoder-only serving session on port
8080 is never stopped, reloaded or contacted by either.

**Blocker found and fixed (model-free).** `scripts/build_speech_query_source_inventory.py` read the
roster receipt's rows as `item["id"]`. `core.roster.freeze_roster` guarantees only `sample_id`; the
`id` extra is optional, `SLURP-DEV-2000-ADDED-V1` declares it (and it equals `sample_id` on all
1,000 of its rows), and `SLURP-STAGE3-CONSTRUCTION-R01` declares the draw extras `stratum`,
`draw_rank` and `min_cosine_to_selected` instead. Step 2a would therefore have raised
`KeyError: 'id'` on R01 before a single byte was read. The builder now reads `id` when present --
so every already-sealed inventory reproduces byte for byte -- and falls back to `sample_id`
(`roster_sample_ids`, covered by `tests/unit/test_stage3_construction_r01_preparations.py`).

## 6. Preparation 4 (not a new tool contact): the prepared supply and the native-contact fit

The last four ROLL-1 placeholders are per-flight bookkeeping the existing flight machinery mints
once steps 1-3 exist; nothing new is registered for them here.

* `prepared_phase_supply.{relpath,sha256}` -- the cell's own model-free first-phase Perception
  supply, built by `core.flight.cli prepare-supply` (`python -m
  speech_aware_evidence_acquisition.core.flight.cli prepare-supply --repo-root ... --data-root ...
  --runtime-root /home/chao --lock-path <umbrella datasets.lock.json> --experiment
  slurp-native-stage3-rollout-r01-v1 --cell <cell> --output <phase-supply-vN.json>`). In practice it
  is invoked through `python scripts/flights/repin_cell.py`, which re-runs `prepare-supply` only
  when the prepared artifact would actually mismatch, re-pins it into the baseline fragment,
  rewrites every dependent composed/protocol hash and then flips `readiness.state` with
  `--set-ready`.
* `native_contact_fit.{run_id,attempt_id,contact_cap}` -- minted at flip time by the same tool, as
  cell B6's registration did. Following the S3-2 naming, the run ids will be
  `SAEA-SLURP-STAGE3-ROLLOUT-R01-V1` (generation), `SAEA-SLURP-STAGE3-ROLLOUT-R01-FIT-V1` (fit) and
  `SAEA-SLURP-STAGE3-ROLLOUT-R01-SMOKE-4-V1` / `-SMOKE-4-FIT-V1` for the four-row smoke; the fit
  batch itself runs through `python scripts/flights/run_fit_batch.py`. The contact cap is the
  graph's own ceiling (`rails.native_episode_config` with `samples=5`: 1 + 2 x (5 + 3 + 1) = 19 per
  row) times the 800 roster rows.
* `preparation_source_receipts[6].sha256` -- the committed roster receipt's own hash. It needs no
  preparation at all and is already measured here:
  **`fdb6521a0863b5f11f7ccea9fba5a1e598d65c5eb05b13a68d1198d5e01ba5f0`**.

## 7. What this document does not authorise

No contact of any kind, no readiness flip, no cell registration, no campaign-plan entry, no queue
append, and no scoring or answer read. The three ledger rows appended to `docs/exposure-ledger.md`
alongside this note are DRAFTS carrying `consumed = no`; each still needs root's countersignature at
a clean tree before the corresponding step may run, and none of them authorises cell ROLL-1 itself.

## 7. Recovery addendum (2026-09-22, coordinator)

Attempt v1 of preparation 1 (`SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS`, scheduled task SAEA-Prep-R01, 19:09-19:21 UTC)
failed: the CPU-only sidecar on port 8081 was killed at 19:21:20 UTC by the SAEA-Serving task entry's orphan reaper
(`pgrep -f "llama-server --host"` + `kill -9`) when the coordinator switched the serving geometry from E21 to SLURP beside
it. Encode 72 ok / 728 failed; the driver refused to promote a partial cache; no promotion receipt exists. Fix: the reaper is
scoped to `--port 8080` in both entry scripts. The one recovery is `SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS-RECOVERY-V1`
(roster key `stage3-construction-r01-recovery`, own run id because the plan budget is cumulative per run id; identical
form and target receipt), registered in the ledger before its first contact. Rule for the recovery: no serving task start or
stop while the sidecar runs. Stage-3 algorithm label (decision 101): `none`, as for the original registration; the recovery fragment is allowlisted in `scripts/checks/stage3_algorithm_label_check.py` because it was in flight when the label landed.

## Stage-3 algorithm label (owner decision 101)

**`none`** -- the three preparations registered here are model-free / preparation cells of Stage-3 item
S3-1 and carry no training-free RL operator; the rollout they feed (ROLL-1) is labelled `shared-rollout`
and the cells that consume its samples are labelled `tfgrpo-semantic-advantage-v1`. The label lives here
as prose rather than in `configs/experiment/slurp-stage3-construction-r01-preprocess.json` because that
fragment's composed config hash is pinned in this note and carried by its DRAFT ledger rows;
`scripts/checks/stage3_algorithm_label_check.py` allowlists it with that reason.

## 8. Prepared configs for preparations 2 and 3 (2026-09-22)

Registered model-free in worktree `/home/chao/saea-worktrees/fable-s3q` (branch `fable/s3q`) on the
commit that carries this section. **Zero model, encoder, tokenizer, scorer, GPU and network
contacts were made by this registration**, no audio sample was decoded, and no utterance text, gold
label or score was read. It authorises nothing: steps 2b, 2c and 3 still need root's countersignature
on their already-drafted exposure rows.

### 8.1 The files

| File | Raw sha256 | What it is |
| --- | --- | --- |
| `configs/preparation/slurp-stage3-construction-r01-speech-query-encoding-protocol-v1.json` | `c7da3e89cf95597a7c31db64e8b222aa04cd8c32df0a328ba0cd1dae7bd2bc06` | the step-2b `saea-speech-query-encoding-protocol-v1` |
| `configs/preparation/slurp-stage3-construction-r01-query-alias-v1.json` | `67d2cb22a5d1fec9b744c14ea4e5e863d0f5d9fa8679a3da6b8d6f9779ea2403` | the step-2c alias **template** (two `PENDING_STEP_2B_*` digests) |
| `scripts/flights/batch/r01_prep2_runtime_config.py` | `d800d9b1391de5b1da69fd8487fd17d38f29d7361fedc0d32a21dd0f4ce1dca3` | mints the step-2b runtime config and prints its sha256 plus launch line |
| `scripts/flights/batch/r01_prep23.sh` | `545409c91bd60ccbf4e205e40ec106e59cb650c2a7cd12febad5e98a6ecb1398` | the runbook root runs **after** step 2b: steps 2c and 3, then the fill values |
| `scripts/flights/batch/r01_prep23_steps.py` | `85e12696ae5e9b396ff970b1bb9764f3d33bb55cd2eec60afb52c22e5b714f4a` | that runbook's model-free helper steps |
| `tests/unit/test_stage3_construction_r01_preparation_configs.py` | `f17e18c7ef76c4f1ba21625caf8d0542c3420584609c17ba2d66c05d4f2a2991` | 32 assertions over both configs, the generator and the runbook |

The protocol is the DEV-2000-ADDED protocol field for field except the seven roster-bound values
(`cache_relpath`, `expected_unique_spans`, `isolation`, `output_relpath`, `query_rows_relpath`,
`roster_sha256`, `sources`), which the test asserts one by one. Its `sources` pins the step-2a
inventory `$SPEECHRL_DATA_DIR/coordination/slurp-stage3-construction-r01-speech-query-source-inventory-v1.json`
sha256 `a4ed13ad67441f5ceaf8be14ef52e3516a6c5f86d1155c6fb754a8ef6b2f771b` from the start, so the
two-correction sequence the DEV-2000-ADDED protocol had to record is not expected here.

**Validated without running the encoder**, through the runtime's own loaders
(`core.speech_preparation_runtime.pinned_json` / `confined`,
`core.preparation_speech_queries.segment_plan`, `contracts.ExecutionPlan.validate`) -- every check
`run_preparation` performs before its first contact: protocol schema and bytes, the pinned source and
encoder bindings, `sources.roster_sha256 == protocol.roster_sha256`, the three confined artifact
paths (all still free), **800 unique spans**, **3491.426125 span seconds** (under the declared 3,492),
and the reproduced split identity `2ece5e51ff781fdec89bef8e7448d8ba88249030d3c8a6478dba5e7c1e621dac`.
The one check deliberately not reproduced is `verify_encoder`, which re-hashes the whole frozen
Omni-Embed-Nemotron directory and belongs to the run itself.

### 8.2 The step-2b runtime config and the exact launch

`core.speech_preparation_runtime.main` refuses unless the runtime config's `study_head` equals the
HEAD of the clean checkout the launch runs from, so that digest cannot exist in a committed document
(it would have to hash the commit that carries it). It is therefore minted, not committed:

```bash
cd /home/chao/saea-worktrees/fable-s3q      # any clean checkout of the registration commit
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD:$PWD/src"
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
source ~/.venvs/speechrl/bin/activate

python -B scripts/flights/batch/r01_prep2_runtime_config.py \
    --repo-root "$PWD" --data-root "$SPEECHRL_DATA_DIR"
```

It writes `$SPEECHRL_DATA_DIR/coordination/slurp-stage3-construction-r01-query-encoding-v1/runtime-config-v1.json`
(refusing to change existing bytes, and refusing a dirty tree) and prints the `sha256` to pass. The
document is the DEV-2000-ADDED one with this roster's values: plan `800` calls / `3492` speech
seconds / `2.0` GPU hours, `split_role` `discovery`, split identity `2ece5e51...`, `protocol_hash` =
the protocol's raw sha256 `c7da3e89...`, `session_id`
`local-nemotron-slurp-stage3-construction-r01-query-v1`, and the umbrella lock
`/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json`. Then:

```bash
python -B -m speech_aware_evidence_acquisition.core.speech_preparation_runtime \
    --config "$SPEECHRL_DATA_DIR/coordination/slurp-stage3-construction-r01-query-encoding-v1/runtime-config-v1.json" \
    --config-sha256 <the sha256 the generator printed> \
    --data-root "$SPEECHRL_DATA_DIR" \
    --source-root "$PWD"
```

Step 2b runs only after `SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS` has closed (it has: the R01
promotion receipt is sealed at sha256 `a1664e34...`), so the two CPU-resident passes never compete
for custody, and never while a serving task is started or stopped.

### 8.3 Step-2b ledger-row values for the countersignature

The row `SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1` is already drafted; the
countersignature needs exactly these values, and every one is what the minted plan claims:

| Field | Value |
| --- | --- |
| run id | `SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1` |
| attempt id | `encode-v1` |
| execution profile | `bounded-discovery-probe` |
| split role | `discovery` |
| split identity hash | `2ece5e51ff781fdec89bef8e7448d8ba88249030d3c8a6478dba5e7c1e621dac` |
| carrier | `slurp` |
| consumed | `no` (until the run seals) |
| calls | `800` (measured: 800 unique spans, one forward each) |
| speech audio seconds | `3492` (measured 3,491.426125) |
| gpu hours | `2.0` (the DEV-2000-ADDED ceiling; about 0.09 expected) |
| protocol hash | `c7da3e89cf95597a7c31db64e8b222aa04cd8c32df0a328ba0cd1dae7bd2bc06` |
| config sha256 | printed by `r01_prep2_runtime_config.py`; binds `study_head` = the registration commit |
| source inventory sha256 | `a4ed13ad67441f5ceaf8be14ef52e3516a6c5f86d1155c6fb754a8ef6b2f771b` |
| roster receipt sha256 | `fdb6521a0863b5f11f7ccea9fba5a1e598d65c5eb05b13a68d1198d5e01ba5f0` |

### 8.4 Steps 2c and 3: the runbook

The committed alias config is a **template**: `core.preparation_vectors` accepts exactly eight keys
and no placeholder, so it is never handed the committed file, and the committed file is never edited
in place. `PENDING_STEP_2B_QUERIES_SHA256` is the step-2b `queries.jsonl` digest and
`PENDING_STEP_2B_RECEIPT_SHA256` is the raw digest of that run's `receipt.json`; the `how_to_fill`
key says so and is stripped on materialisation. After step 2b seals:

```bash
bash scripts/flights/batch/r01_prep23.sh          # PREP23_DRY=1 to rehearse without writing
```

It (A) verifies the sealed step-2b receipt (schema, `SEALED`, run and attempt id, protocol sha,
800 `logical_encoder_contacts`, the source-inventory sha) and re-hashes `queries.jsonl` against the
receipt's own `query_rows_sha256`, then materialises the runnable alias config to
`$SPEECHRL_DATA_DIR/coordination/slurp-stage3-construction-r01-query-encoding-v1/query-alias-v1.json`;
(B) runs step 2c with that file's sha256; (C) re-hashes the 800-row segment export the 2c receipt
declares; (D) runs preparation 3 (`scripts/build_slurp_query_content_derivative.py`, `--ledger-row
SAEA-SLURP-STAGE3-CONSTRUCTION-R01-QUERY-VECTOR-EXPORT-V1`); and (E) prints every output path with
its sha256 plus the ROLL-1 fill values:

* `knowledge_stores.intent-boundaries.phase_supply.perception.query_source` -> kind
  `sealed-segment-vectors`, relpath `vectors/slurp-stage3-construction-r01-v1/query-vectors-speech-segments.jsonl`,
  sha256 from the 2c receipt, ledger row `SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1`;
* `knowledge_stores.train-exemplars.phase_supply.solver.query_source` -> kind `sealed-vectors`,
  relpath `vectors/slurp-stage3-construction-r01-v1/query-vectors-speech-content-v1.jsonl`, sha256
  from the derivative, ledger row `SAEA-SLURP-STAGE3-CONSTRUCTION-R01-QUERY-VECTOR-EXPORT-V1`;
* `preparation_source_receipts[6].sha256` -> `fdb6521a...` (already measured in section 6);
* `preparation_source_receipts[7]` -> `preparation-runs/SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json`, root `data`.

**One open choice for `preparation_source_receipts[8]`, which the runbook prints both ways rather
than deciding silently.** Section 4 of this note assigns [8] to preparation 3's own receipt
(`vectors/slurp-stage3-construction-r01-v1/query-vectors-speech-content-v1.provenance.json`), while
the DEV-2000-ADDED precedent `configs/baseline/slurp-native-default-plan-dev2000-added-baseline-v1.json`
instead pins the 2c alias receipt (`prepared/SAEA-SLURP-DEV2000-ADDED-ALIAS-V1/query-dimension-alias.json`,
its index 5) and never pins the content provenance at all. The re-pin should pin one and **append**
the other rather than drop it; both digests are printed.
