# SLURP test SAMPLE preparations, v1

Owner decision 156 of 2026-09-27 (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`, row
156; the owner's words, translated: "The preparation work may run ahead."): the first-contact gate of row 151
is lifted for the three PREPARATION run ids of `SLURP-TEST-SAMPLE-3010-V1` only. Each is registered,
countersigned under that row, and run on CPU where the registered path allows, beside the GPU queue, inside
the 8-worker preparation cap. The six MILESTONE read ids keep row 151's gate; none of them is registered,
configured or launchable here, and the runner refuses any of them outright.

**This note registers the three preparations and makes them runnable. It runs nothing.** Every artifact
below was derived model-free, label-free and media-free on branch `fable/testprep` (worktree
`/home/chao/saea-worktrees/fable-testprep`, from master `417930d6`): zero model, server, encoder, embedder,
tokenizer, scorer, GPU and network contacts, no media byte and no container header opened, and no gold,
sentence, transcript or annotation read. The three exposure rows (section 4) are REGISTERED BEFORE CONTACT
and carry the pending root-countersignature marker.

Authority: the signed allowance `docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json`
(status `authorised`, owner decision 151, sha256
`c2ae2c4eb2142b5aef27d85c04c7dcd55952c105b469fd195592c71cb6bb331b`), pinned by every plan below and left
byte-identical. Template: the FULL registration of 2026-09-23,
`docs/readiness/2026-09-23-slurp-test-full-preparations-v1.md`, whose configs and draft rows are untouched.

## 1. What was derived, and how

| Artifact | Raw sha256 | How |
| --- | --- | --- |
| `configs/dataset/slurp-speech-native-test-sample-3010.json` | `854cad00…` | the runtime view: the committed FULL view restricted to the 3,010 roster ids (`scripts/flights/testsample/derive_test_sample_preparations.py runtime-view`) |
| `configs/experiment/slurp-test-sample-3010-preprocess.json` | `61089583…` | the FULL fragment with run id, allowance pin and prose swapped |
| `configs/preparation/slurp-test-sample-3010-speech-query-encoding-protocol-v1.json` | `e455c588…` | the FULL protocol with the roster-bound values swapped |
| `configs/preparation/slurp-test-sample-3010-query-alias-v1.json` | `ea2330a8…` | the FULL alias template with the roster-bound values swapped |
| `$SPEECHRL_DATA_DIR/coordination/slurp-test-sample-3010-speech-query-source-inventory-v1.json` | `77fce38e…` | step 2a, pinned now, written by the runner at launch (not yet on disk) |

The runtime view carries the FULL view's item records unchanged, its own identity fields
(`split_name` `TEST-SAMPLE`, seed 20260927, split identity `0164dabf…`, `source_binding_sha256` = the
canonical SHA-256 of the sample roster receipt, `runtime_view_sha256` `862bef37…`), and the FULL view's D1
supplement triple unchanged: `docs/receipts/artifacts/d1-slurp-test-full.json` closes over all 13,078 test
recordings, a superset of the sample, and the gate reader looks each sample id up in it.

The source inventory is where this registration departs from the FULL one. The FULL inventory was built by
`scripts/build_speech_query_source_inventory.py`, which re-hashes every media file and reads every header;
a registration of the sample may not open test media. The sample's inventory is instead a byte-reproducible
function of the committed runtime view: `id`, `media_relpath` and `audio_sha256` are copied and
`source_frames` = `audio_seconds x sample_rate_hz`, exact (the tool refuses a non-integer frame count). It
carries no timestamp, so its SHA-256 is pinned in the protocol before contact. Nothing is weakened:
`core.preparation_speech_queries` re-hashes every media file and re-reads every header against these rows
before the first forward, and the runner additionally compares every derived row with the media-measured
FULL inventory (`c16ede61…`) when that file is present, before the attempt is opened.

**Proof that nothing else changed** (`tests/unit/test_slurp_test_sample_preparations.py`): the sample's
composed preprocess config differs from the FULL one only in `experiment_id`, `owner_allowance`, `purpose`,
`items`, `count`, `audio_seconds_total`, `split_identity_hash`, `split_name`, `seed`,
`source_binding_sha256` and `runtime_view_sha256`; the protocol and alias template differ from the FULL ones
only in their roster-bound fields; the FULL composed hash is still its registered `9312a112…`.

## 2. The three preparations

| # | Run id | Profile | Calls | Speech s | GPU h | Device |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | `SAEA-SN-TEST-SAMPLE-3010-PREPROCESS` | `bounded-discovery-probe` | 3,010 | 8,207 | 1.0 | CPU-only sidecar, port 8081, `-ngl 0`; concurrent with the GPU queue |
| 2 | `SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1` | `bounded-discovery-probe` | 3,010 | 8,207 | 2.0 | GPU (the encoder loads on CUDA); queued behind the flight queue |
| 3 | `SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1` | `model-free-check` | 0 | 0 | 0 | CPU, zero contacts |

Speech seconds are the ceiling of the roster's measured 8,206.436875 s; the allowance's expected 8,206 is that
figure rounded down and binds no budget (a plan declaring 8,206 would be refused by the runtime's own audio
check). Preparation 1: composed config `9a1814ad5aced59d6a7f5692ebaf9efd7909927a3799bbfdf8f7b6b7dfef0fbb`,
attempt `attempt-packets-test-sample-3010-v1`, roster key `test-sample-3010` in
`scripts/slurp_evo_fold_preprocess.py`, promotion receipt `TEST-SAMPLE-3010-promotion.json`; about 4.1 h of
wall clock at `--workers 4` (the R01 rate scaled by audio; row-scaled bound 6.6 h), 0.0 GPU hours consumed.
Preparation 2: attempt `encode-v1`, `cpu_workers` 8 for the audio prefetch, about 751 s at the
DEV-2000-ADDED rate; the declared 2.0 GPU hours is also the runtime's wall-clock stop.

The speech-query encoding is **not** CPU-only: `core.speech_embedding.load_stack` moves the frozen
Omni-Embed-Nemotron-3B to `cuda`. It therefore waits for the GPU flight queue; the runner refuses it while
`core.flight.cli` or `batch_driver.sh` runs, and while any CPU-resident llama-server other than the
port-8080 service is up (so it never overlaps the packet sidecar).

## 3. The runner

`scripts/flights/testsample/prep_test_sample.sh` (helper `prep_test_sample_steps.py`, scheduled-task entry
`prep_test_sample_task_entry.sh`) runs the three in order through the existing generic runners: stage
`packets` calls `scripts/flights/batch/prep_generic_task_entry.sh` with `PREP_ROSTER=test-sample-3010`;
stage `queries` runs 2a, then `scripts/flights/batch/prep_generic_steps.py`'s own `runtime-config`,
`materialise`, `alias-receipt` and `report` steps with this roster's `PreparationSet` added in memory (the
generic file is unchanged; its runtime-config document is wrapped only to carry the `owner_allowance` pin a
`final-report` plan needs), then `core.speech_preparation_runtime`, `core.preparation_vectors` and
`scripts/build_slurp_query_content_derivative.py`. Refusals: a dirty checkout; the allowance's bytes or
status; any MILESTONE read id in a stage or a bound config; any exposure row of the stage still marked
pending or without a root countersignature; a second CPU-resident llama-server; a GPU flight (queries
only). A sealed step is skipped, never re-run. The minted step-2b plan is re-proved against
`contracts.gate_exposure._require_final_report_isolation`, which the tool-plan admission of
`core.speech_preparation_runtime` does not itself run. `--check` is model-free and media-free.

Countersign-then-run, for the coordinator: (1) merge `fable/testprep` into master between flights; (2) in
`docs/exposure-ledger.md`, replace each row's pending parenthesis with
`(root countersigned <UTC> by <who>, owner decision 156)` and commit at a clean tree; (3)
`bash scripts/flights/testsample/prep_test_sample.sh --check` must print no refusal; (4) launch stage
`packets` as a scheduled task now (it runs beside the flight queue); (5) launch stage `queries` after the
flight queue drains and the sidecar has stopped.

## 4. Exposure rows

Appended to `docs/exposure-ledger.md` under "SLURP test sample: the three label-free preparations of
SLURP-TEST-SAMPLE-3010-V1", all `consumed = no`, all REGISTERED BEFORE CONTACT with the root
countersignature pending, each stating owner decision 156, `reads_labels` false and its device.

## Stage-3 algorithm label (owner decision 101)

**`none`** -- preparation cells that carry no training-free RL operator; out of scope for
`scripts/checks/stage3_algorithm_label_check.py` exactly as the TEST-FULL preparations are.
