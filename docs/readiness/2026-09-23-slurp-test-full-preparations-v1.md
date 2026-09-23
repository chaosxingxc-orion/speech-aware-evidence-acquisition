# SLURP-TEST-FULL preparation plan, v1

Owner decision 99 of 2026-09-22 and owner decision 107 of 2026-09-23
(`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`): exactly ONE complete official
SLURP test-split read happens at the end of Stage 3, and its preparations -- roster freeze, D1 media
supplement, featcache packets, speech query vectors -- are registered now and built in parallel ahead
of time so the read waits on nothing. This document states what is ready, what the owner's decision
108 must say, and what every remaining step will cost.

**It registers no cell, authorises no contact, flips no readiness state, mints no decision receipt and
countersigns no ledger row.** Every number below was measured model-free and label-free in worktree
`/home/chao/saea-worktrees/fable-s3test` (branch `fable/s3test`) on study commits `947e79e4`,
`d8c184c4`, `016fa592`, `042b8b72` and `8683c636`: zero model, tokenizer, encoder, embedder, scorer,
GPU and network contacts; no audio sample was decoded; and no utterance text, transcript, gold label,
intent or slot annotation of any test row was opened.

Protocol: `docs/readiness/2026-09-19-slurp-test-split-one-read-protocol-v1-draft.md` (raw sha256
`b5e910e31a4986307edbac15101867ab97c42152d88d4f2cd086106630eac54b`). Precedent throughout: the
SLURP-STAGE3-CONSTRUCTION-R01 preparation chain
(`docs/readiness/2026-09-22-slurp-stage3-construction-r01-preparations-v1.md`).

## 0. The roster in one paragraph

`SLURP-TEST-FULL-13078-V1` (`docs/receipts/rosters/slurp-test-full-13078-v1.json`, raw sha256
`b925e90ab99727e7d0ff9fc4ec6b7c91a0d86bff0a5b0a4746b9cc98237b19c3`): the **complete** official SLURP
test split -- **13,078 recordings over 2,974 utterances**, both microphone channels (**6,281
headset**, **6,797 far-field**), no subsampling, no filtering, no reserve, `excluded_count` 0.
`roster_role: evaluation`, `split_role: final-report`, seed 20260923 on a take-all freeze through
`core.roster.freeze_roster`. Split identity hash
`7247647b8c8b37becd564b7031691565d4e6b09d8e124823054906d36372c95d` (the carrier-prefixed
`core.roster` convention an `ExecutionPlan` declares); the frozen bare-id carrier identity is
`3f7063cb8b1e60d69c383d2215b5f244bbd7164d484010193a093a5e879389bd`, unchanged from
`docs/receipts/knowledge/slurp-split-identity.json`. **Audio: 36,911.9388125 seconds** (10 h 15 min
12 s; mean 2.8224 s per recording), **700,033,078 media bytes**, one sample rate (16,000 Hz). The
declared ceiling everywhere below is `36912` (`ceil(36911.9388125)`), the form every SLURP roster
uses.

Runtime view `configs/dataset/slurp-speech-native-test-full.json` (raw sha256
`127556a475996603862302ef68196d80ec075818cd88a407e37d42387b664e34`, canonical `runtime_view_sha256`
`c657d4fe3ea05d6e655707530f0e30ae8f67dd1671a2a475cc682422903e7744`, `source_binding_sha256`
`6812ace680e7bd2d521b6834f7120adfbed81b5d112be8bb9c90f440d5505f6e`).

## 1. What is ready

| Artifact | Raw sha256 | What it is |
| --- | --- | --- |
| `docs/receipts/rosters/slurp-test-full-13078-v1.json` | `b925e90a…` | the frozen identity of all 13,078 recordings |
| `docs/checks/…/2026-09-23-slurp-test-roster/disjointness.json` | `f6b759d2…` | the four-pass disjointness proof (section 3) |
| `configs/dataset/slurp-speech-native-test-full.json` | `127556a4…` | the label-free runtime view |
| `docs/receipts/artifacts/d1-slurp-test-full.json` | `d68bd784…` | the additive D1 media supplement, 13,078 entries |
| `docs/checks/…/2026-09-23-slurp-test-full-packets/media-inventory.json` | `6bc45551…` | aggregate media facts + measured CPU throughput + cache warmth |
| `docs/checks/…/2026-09-23-slurp-test-full-packets/packet-preparation-plan.json` | `23e52fa6…` | what ENCODE and PROMOTE still have to do |
| `docs/checks/…/2026-09-23-slurp-test-full-packets/d1-gate-verification.json` | `64d78619…` | the real gate reader over all 13,078 rows: PASS |
| `docs/receipts/owner/2026-09-23-slurp-test-split-allowance-v1.json` | `7b7bf3dc…` | the allowance receipt, `status: "pending-owner"` |
| `configs/experiment/slurp-test-full-preprocess.json` | `286b7cf0…` | the packet-promotion experiment fragment |
| `configs/preparation/slurp-test-full-speech-query-encoding-protocol-v1.json` | `527009ef…` | the step-2b encoding protocol, `cpu_workers` 8 |
| `configs/preparation/slurp-test-full-query-alias-v1.json` | `f8432e4f…` | the step-2c alias template (two `PENDING_STEP_2B_*` digests) |
| `scripts/build_slurp_test_full_roster.py` | `913921d0…` | the roster + disjointness generator |
| `scripts/build_slurp_test_full_runtime_view.py` | `6df76c60…` | the runtime view + inventory + packet plan generator |

Also built, outside Git, model-free and zero-contact:
`$SPEECHRL_DATA_DIR/coordination/slurp-test-full-speech-query-source-inventory-v1.json`, sha256
`c16ede61a994ef5b2920ab0b9a446203574ee7c731e4c8cae7e5a31e1306ca5f` -- 13,078 rows, `roster_sha256`
`b925e90a…`, split identity `7247647b…`, `audio_seconds_total` 36,911.938812. It is the step-2a
source inventory the encoding protocol pins from the start, so the two-correction sequence the
DEV-2000-ADDED registration had to record is not expected here.

Tests: `tests/unit/test_final_report_split_role.py` (54), `tests/unit/test_slurp_test_full_preprocess_roster.py`
(24), `tests/unit/test_slurp_test_full_preparation_configs.py` (19).

## 2. The allowance mechanism, and what decision 108 must say

No contract admitted a final-reporting split role before this change. `STAGE2_SPLIT_ROLES` still
admits exactly `{"discovery", "dev"}`, and `"confirmatory"` is still refused outright with the
message protocol section 6.1 quotes. What is new is one fail-closed role:

* `contracts.plan.FINAL_REPORT_SPLIT_ROLE = "final-report"` -- the name protocol section 6.3 asks for
  ("a role named for what it is ... never reuse `dev`"). Section 6.2 records why reusing `dev` would
  be the relabeling the guard forbids: `dev` means "legal to calibrate against, never a
  final-reporting split".
* `contracts.plan.require_owner_split_allowance` refuses such a plan unless **all nine** of: the plan
  carries `owner_allowance = {path, sha256}`; the path is repo-relative under `docs/receipts/owner/`;
  the profile is exactly `bounded-discovery-probe`; the receipt's **bytes** hash to the pinned
  sha256; it is a `saea-owner-split-allowance-v1` document of this study; its `status` is exactly
  `"authorised"`; its `split` names this plan's carrier **and** split identity hash; its
  `permitted_run_ids` contains this run id and partitions into disjoint `read_run_ids` +
  `preparation_run_ids`; and it names the dated owner decision and states in `venue` why the read is
  not promoted to a `papers/<slug>` repository. Every failure raises `ExecutionScopeError` naming
  what is missing.
* `contracts.gate_exposure._require_final_report_isolation` adds, at gate time and from live bytes:
  no construction-visible arm; a **re-proof** of roster disjointness against every committed roster
  receipt of the carrier and every knowledge store / exemplar pool snapshot under the data root; and
  **one attempt** per permitted read run id (a second is refused even as a recovery), two for a
  preparation run id.
* `scripts/slurp_evo_fold_preprocess.py` calls the same verifier **before** it opens the data root,
  so `--preflight-only` and `--promote-only` refuse too -- neither of those builds an
  `ExecutionPlan`, and without that call a 700 MB media pass would have run over the test split while
  the allowance was pending.

Today the committed receipt says `status: "pending-owner"`, so **every** `final-report` plan and
every preparation is refused, with the message `owner allowance receipt … status is 'pending-owner',
not 'authorised'`.

**Decision 108 must state four things.**

1. **Venue.** Protocol section 6 puts two remedies and recommends the first. **Remedy A** promotes
   the read to an independent `papers/<slug>` repository under
   `OWNER_GO_AND_PAPER_EXECUTION_CONTRACT`; that is what the paper gate exists for and it leaves this
   study's guard untouched. **Remedy B** keeps the read here behind a dated amendment plus this
   paired code change. If B, the amendment must say **why** the read is not being promoted, and that
   sentence becomes the receipt's `venue` field. The field is currently the honest placeholder "no
   reason has been given".
2. **The preparations' role.** The three preparation passes are label-free encoder contacts on test
   media and a zero-contact derivative. They do not read the split's answer surface, but they DO
   touch its rows, so they carry the same machine role and the same allowance as the read. Decision
   108 must say so explicitly, or say that the preparations are promoted with the read to the papers
   carrier. There is no third option that is honest: a preparation under `dev` would be exactly the
   relabeling section 6.2 rejects.
3. **The direct arm** (protocol section 5(c), left open at section 9 item 2). The draft recommends
   flying it in the same registered read, at one extra contact per row, for the only internal
   contrast the read can have. The allowance already names
   `SAEA-SLURP-TEST-FULL-DIRECT-V1`; if the owner declines, that run id is struck from
   `permitted_run_ids` and the receipt is re-pinned.
4. **The text-level disjointness pass** (protocol section 2.3 item 3, section 9 item 3). It is
   recorded as NOT RUN, with its reason. Decision 108 may leave it not run -- the id-level proof is
   then the whole proof -- or may admit a hash-only pass inside a sealed process, which is a
   successor receipt, never an edit of these bytes.

**How the unlock works, mechanically.** Flipping `status` to `"authorised"` changes the receipt's
bytes, so every pinned sha256 that names it breaks and every composed config hash that carries the
pin moves. That is deliberate: the ruling forces a visible, countersigned re-pin of each preparation
rather than silently unlocking plans that were registered while it was pending. The sequence is:
owner edits the receipt (status, `dated_owner_decision`, `venue`) -> re-pin
`configs/experiment/slurp-test-full-preprocess.json` -> re-run the composed-hash-carrying rows of
section 6 -> root countersigns the three ledger rows at a clean tree -> the steps run in the order of
section 5.

## 3. Disjointness: proved at freeze, re-proved at gate time

`docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-test-roster/disjointness.json`
(sha256 `f6b759d2…`), **60 sources checked, verdict CLEAN**:

| Pass | What was compared | Result |
| --- | --- | --- |
| 1. by recording id | every `slurp`-carrier roster receipt (36), every `slurp` probe-sample receipt, every `slurp` probe-binding config, and every knowledge store / exemplar pool snapshot under the data root (`source_sample_ids` only, never `values` or `facets`) | **0 shared** on every pair |
| 2. by utterance | both the full `slurp:<split>:<number>` id and the bare SLURP prompt number, because the split token alone would make every cross-split comparison trivially empty | **0 shared** on every pair |
| 3. by text | **NOT RUN** -- protocol section 9 item 3 leaves its admissibility undecided and this build never opens the test annotations | recorded with its reason |
| 4. exposure closure | both identity hashes searched across every ledger table | **no consumed row**; the split is unread |

Pass 4's criterion is the protocol's own: "appears in no **consumed** exposure-ledger row". The three
DRAFT rows of section 6 are written **after** this receipt was minted and carry `consumed = no`, so a
later re-run of the generator reports them and still returns UNREAD.

The gate does not trust any of this. `_require_final_report_isolation` re-intersects the roster's ids
from live bytes on every gate open, and refuses the touch on the first shared id.

## 4. The four preparations

### 4.1 D1 media supplement (DONE, model-free)

`docs/receipts/artifacts/d1-slurp-test-full.json` (sha256 `d68bd784…`), built with the existing
roster-parameterised builder -- reused, not forked:

```bash
python scripts/build_slurp_stage3_construction_r01_d1_supplement.py \
    --roster-receipt docs/receipts/rosters/slurp-test-full-13078-v1.json \
    --runtime-view configs/dataset/slurp-speech-native-test-full.json \
    --output docs/receipts/artifacts/d1-slurp-test-full.json \
    --sample-id-prefix slurp:test: --workers 8 --write --pin-runtime-view
```

13,078 entries, **0 skipped**: the immutable D1 artifact closes over SLURP devel only, so no test row
was already inside it. `parent_d1_sha256`
`9c10fad1e5b625f977a5bdc71ed0c782e5d5c76c7a13af11ce811c5e152d35e3`, `manifest_sha256`
`58400dbb2b796f4e476a5ce4b6f2ee2ea6c04cc3b36e088e82b70c5d1c5cffc5`, `total_bytes` 700,033,078. Its
own `ids_sha256` reproduces `3f7063cb…`, an independent cross-check that the supplement covers exactly
the whole split. Every media file was re-hashed; only the container header was read.

**The gate reader accepts it.** `contracts.FrozenCoreGate.verify_media_identity` -- the same reader
the frozen-core gate uses before a model touch -- was run over all 13,078 rows against the pinned
supplement: **PASS**, 0 rows from base D1, 13,078 from the supplement, 97.1 s, zero contacts
(`docs/checks/…/2026-09-23-slurp-test-full-packets/d1-gate-verification.json`, sha256 `64d78619…`;
reproduce with `python scripts/build_slurp_test_full_runtime_view.py --write --verify-d1-gate`).

One finding to report rather than paper over: the builder's `split_role == "test"` tripwire is
narrow. It refuses that literal value, which no roster in this repository has ever used, and it is
not -- and never was -- the guard that keeps a held-out split safe: a D1 media supplement carries
media identity only and no annotation of any kind. The guard that governs this roster is the owner
allowance. The builder now says so in a comment rather than silently passing.

### 4.2 Preparation 1 of 3 -- speech packet promotion (ENCODE + PROMOTE)

* **Run id** `SAEA-SN-TEST-FULL-PREPROCESS`, attempt `attempt-packets-test-full-v1`.
* **Roster key** `test-full` in `scripts/slurp_evo_fold_preprocess.py`'s `PREPROCESS_ROSTERS`,
  appended at the end of the table; experiment fragment
  `configs/experiment/slurp-test-full-preprocess.json` (raw sha256 `286b7cf0…`). Composed config
  `q4km-preprocess-featcache-cpu-sidecar` / `slurp-speech-native-test-full` /
  `speech-native-preprocess` / `slurp-test-full-preprocess`, **config hash**
  `9312a112b789731088ef6627f785615acff615db17302b7dc8d27b4b7a70c079` (computed through
  `core.config.compose`, never hand-typed). **This hash moves when the allowance is re-pinned.**
* **Coverage, measured not assumed**: **0 of 13,078** rows are warm in the legacy feature cache
  `/home/chao/feat-cache/slurp-q4km`, and **0** have a leaf directory under the resident packet root
  `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a`. No SLURP test row has ever been encoded here,
  so the ENCODE pass is 13,078 contacts and none of them is a re-verification.
* **Expected counts**: 13,078 frozen-core contacts at `max_tokens: 1`; 36,911.9388125 speech seconds
  (declared 36,912); 13,078 new promoted packets; `TEST-FULL-promotion.json` written once,
  create-only.
* **Expected GPU hours**: **0.0 actually consumed** -- the sidecar runs `-ngl 0
  --no-mmproj-offload` and leaves the GPU to the resident serving session. The declared plan ceiling
  is `1.0`, the value every preprocessing roster above uses.
* **Expected wall clock**: R01 measured **800 rows / 3,491.426 audio seconds in 6,268 s at
  `--workers 4`**. Encoding cost tracks audio length, so the audio-scaled projection is
  6,268 x (36,911.939 / 3,491.426) = **66,264 s = 18.4 h**. The row-scaled bound is
  13,078 x 7.835 = 102,466 s = 28.5 h; the true figure should sit near the audio-scaled end because
  the test split's mean recording (2.82 s) is shorter than R01's (4.36 s). Either way this is the
  longest CPU pass this repository has run, and it is a scheduled-task decision, not a foreground
  one. `--workers 8` is available and the protocol's own `cpu_workers` ceiling is 8, but the sidecar
  serves `-np 4`, so raising it means raising `-np` too -- a serving-geometry change the coordinator
  owns.

Command line (not run by this package; the row needs root's countersignature first, and the driver
refuses it today anyway):

```bash
cd /home/chao/saea-worktrees/<clean checkout>
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD:$PWD/src"
export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
source ~/.venvs/speechrl/bin/activate

# zero-contact preflight (D1 media identity for all 13,078 rows + the warm-cache count)
python scripts/slurp_evo_fold_preprocess.py --roster test-full --preflight-only

# ENCODE (13,078 contacts on the CPU-only sidecar, port 8081) + PROMOTE (0 contacts)
python scripts/slurp_evo_fold_preprocess.py --roster test-full --run \
    --workers 4 --promote-workers 8 \
    --output docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-test-full-packets/preprocess-report.json
```

Both refuse today with `owner allowance receipt … status is 'pending-owner', not 'authorised'`,
before the first media file is opened.

### 4.3 Preparation 2 of 3 -- speech query vectors (an encoder contact)

* **Run id** `SAEA-SLURP-TEST-FULL-SPEECH-QUERY-ENCODING-V1`, attempt `encode-v1`.
* **Step 2a (DONE, model-free)**: the source inventory named in section 1, sha256 `c16ede61…`.
* **Step 2b (the contact)**: `configs/preparation/slurp-test-full-speech-query-encoding-protocol-v1.json`
  (raw sha256 `527009ef…`) -- the R01 protocol field for field except the roster-bound values and
  `cpu_workers` **8**: `expected_unique_spans` 13,078, `roster_sha256` `b925e90a…`, the
  cache/output/query-rows relpaths renamed to this roster, and an isolation clause that says the
  split's answer surface stays untouched. The frozen Omni-Embed-Nemotron-3B retrieval tool, prompt
  `query: `, dimension 2048, one forward per recording.
* **Step 2c (zero contacts)**: `configs/preparation/slurp-test-full-query-alias-v1.json` (raw sha256
  `f8432e4f…`), the `content` -> `intent-boundary` alias TEMPLATE. Its two `PENDING_STEP_2B_*`
  digests are bound by the roster-agnostic R01 helper
  `scripts/flights/batch/r01_prep23_steps.materialise_alias_config`, reused verbatim; the committed
  bytes stay a template and are never edited in place.
* **Expected counts**: **13,078 encoder contacts**, 36,911.9388125 speech seconds (declared 36,912),
  13,078 unique spans (verified through `core.preparation_speech_queries.segment_plan` over the
  inventory: one span per recording, none over the 120 s boundary). Zero frozen-core contacts, zero
  answers, zero scoring.
* **Expected GPU hours**: about **0.94**. The DEV-2000-ADDED receipt records `elapsed_seconds`
  273.14 for 1,000 contacts / 2,983.527 speech seconds, so
  273.14 x (36,911.939 / 2,983.527) = **3,379 s = 56 min** at `cpu_workers` 4; the row-scaled bound
  is 3,572 s = 60 min. `cpu_workers` 8 doubles the audio prefetch, not the encoder forward, so treat
  56-60 min as the estimate and not a ceiling. The declared plan ceiling is **4.0** GPU hours (the
  precedent's 2.0 scaled for thirteen times the rows).
* **The runtime config is minted, never committed.** `core.speech_preparation_runtime.main` refuses
  unless the runtime config's `study_head` equals the HEAD of the clean checkout the launch runs
  from, so that digest cannot exist in a committed document. Its `plan` block must carry
  `"split_role": "final-report"` and the `owner_allowance` pin, because `run_preparation` validates
  `ExecutionPlan(**config["plan"])` before its first contact -- which is exactly where the refusal
  fires today. `scripts/flights/batch/r01_prep2_runtime_config.py` is R01-specific; a test-full
  sibling (same document shape, this roster's values) is minted at run time.

```bash
# 2b -- THE CONTACT: 13,078 frozen retrieval-encoder forwards
python -B -m speech_aware_evidence_acquisition.core.speech_preparation_runtime \
    --config "$SPEECHRL_DATA_DIR/coordination/slurp-test-full-query-encoding-v1/runtime-config-v1.json" \
    --config-sha256 <the sha256 the generator printed> \
    --data-root "$SPEECHRL_DATA_DIR" --source-root "$PWD"

# 2c -- ZERO-CONTACT dimension alias: content -> intent-boundary
python -B -m speech_aware_evidence_acquisition.core.preparation_vectors \
    --config "$SPEECHRL_DATA_DIR/coordination/slurp-test-full-query-encoding-v1/query-alias-v1.json" \
    --config-sha256 <sha256 of that materialised file> \
    --repo-root "$PWD" --data-root "$SPEECHRL_DATA_DIR"
```

### 4.4 Preparation 3 of 3 -- the content-dimension derivative (model-free)

* **Run id** `SAEA-SLURP-TEST-FULL-QUERY-VECTOR-EXPORT-V1`, profile `model-free-check`.
* Registers **no new tool**: it is R01's step 3 on this roster, through the generic CLI.

```bash
python scripts/build_slurp_query_content_derivative.py \
    --source-relpath vectors/slurp-test-full-v1/query-vectors-speech-segments.jsonl \
    --source-sha256 <as printed by step 2c> \
    --out-dir vectors/slurp-test-full-v1 \
    --out-name query-vectors-speech-content-v1.jsonl \
    --ledger-row SAEA-SLURP-TEST-FULL-QUERY-VECTOR-EXPORT-V1
```

* **Expected counts**: 13,078 rows; **0 model / encoder / tokenizer / network contacts, 0 speech
  seconds, 0 GPU hours**. It constructs no `ExecutionPlan` at all -- the plan validator requires
  finite POSITIVE calls, GPU hours and speech seconds by design, and a pass that touches no model
  must not reserve one contact of head-room -- so the allowance's profile rule does not bind it. It
  is named in `permitted_run_ids` anyway, because it is a derivative of test-split media and its row
  must carry the owner's name like its parents.

## 5. Order

| # | Step | Contacts | Depends on |
| --- | --- | ---: | --- |
| 0 | owner decision 108; re-pin the fragment; countersign the three rows | 0 | -- |
| 1 | ENCODE + PROMOTE packets (`SAEA-SN-TEST-FULL-PREPROCESS`) | 13,078 frozen-core | the committed roster + runtime view + D1 supplement |
| 2a | speech-query source inventory (**already built**) | 0 | the same two files |
| 2b | speech-query encoding (`…-SPEECH-QUERY-ENCODING-V1`) | 13,078 encoder | 2a; run after step 1 closes so the two CPU-resident passes never compete for custody |
| 2c | segment dimension alias | 0 | 2b |
| 3 | content-dimension derivative (`…-QUERY-VECTOR-EXPORT-V1`) | 0 | 2c |
| 4 | the read itself (section 7) | see 7 | 1, 2, 3, the v2.0 lock, and a Stage-3 close |

Steps 1 and 2b are CPU-resident passes; per owner decision 77 each launches as its own scheduled task
rather than as one long-lived process, and the resident serving session on port 8080 is never
stopped, reloaded or contacted by either. **No serving task start or stop while the sidecar runs**
(the R01 recovery addendum's rule: an unscoped orphan reaper killed that sidecar mid-pass).

## 6. DRAFT exposure-ledger rows

Three rows are appended to `docs/exposure-ledger.md` beside this note, all `consumed = no`, all with
scope word **REGISTERED (draft, owner allowance + root countersignature pending)**. None of them
authorises anything: each still needs decision 108 to flip the allowance to `authorised`, a re-pin of
the composed hash it quotes, and root's countersignature at a clean tree.

| Run id | Profile | Calls | Speech seconds | GPU hours |
| --- | --- | ---: | ---: | ---: |
| `SAEA-SN-TEST-FULL-PREPROCESS` | `bounded-discovery-probe` | 13,078 | 36,912 | 1.0 |
| `SAEA-SLURP-TEST-FULL-SPEECH-QUERY-ENCODING-V1` | `bounded-discovery-probe` | 13,078 | 36,912 | 4.0 |
| `SAEA-SLURP-TEST-FULL-QUERY-VECTOR-EXPORT-V1` | `model-free-check` | 0 | 0 | 0 |

## 7. The read's own cost (protocol section 7.3), recomputed from the measured audio

The read's own run ids, from protocol section 7.1 and named in the allowance's `read_run_ids`:
**`SAEA-SLURP-TEST-FULL-LOCKED-SYSTEM-V1`** (the locked default plan at the v2.0 lock commit, on all
13,078 rows) and, only if section 5(c) is authorised, **`SAEA-SLURP-TEST-FULL-DIRECT-V1`**. Each gets
exactly ONE attempt; the gate refuses a second even as a recovery. **No smoke on test rows exists**:
the structural smoke runs on development rows at the lock commit, and the test split never sees a
rehearsal.

The protocol's table was an ex-ante estimate against "about 37,400 s" of unique test audio. The
measured figure is **36,911.9388125 s**, so the repeated-audio column drops slightly. Per-row costs
are the sealed measurements protocol section 7.3 names: the B4b replicate's merged manifest realized
**5.021 contacts per row**, **3.4651 GPU hours per 1,080 rows** (0.00321 per row) and **15,487.59
repeated speech seconds against 3,084.53 s unique** (a 5.021x repeat factor).

| Quantity | Locked system | Direct arm (if authorised) |
| --- | ---: | ---: |
| Rows | 13,078 | 13,078 |
| `planned_model_calls` | about **65,665** (13,078 x 5.021); ceiling at 11 contacts/row **143,858** | 13,078 |
| `planned_gpu_hours` | about **42** (13,078 x 0.00321) | scaled from the locked direct plan's own pass |
| `planned_speech_audio_seconds` (repeated, as metered) | about **185,336** (36,911.94 x 5.021) | **36,912** |
| Official complete scoring jobs | 1 | 0 (scored in the same job) |

Preparations, for the same table: **26,156 contacts** (13,078 frozen-core + 13,078 encoder),
**73,824 declared speech seconds** (36,912 x 2), **5.0 declared GPU hours** against about 0.94
expected -- plus roughly **19-19.5 h of CPU wall clock**, which is the real cost of this half and
the reason decision 107 asked for it to be built in parallel ahead of time.

All plan values are **recomputed at freeze** from the locked plan's sealed per-row cost; the table is
an ex-ante estimate to inform the venue decision, not a registered value.

## 8. What this document does not authorise

No contact of any kind, no readiness flip, no cell registration, no campaign-plan entry, no queue
append, no scoring or answer read, and no second read of anything. The three ledger rows appended
beside it are DRAFTS carrying `consumed = no`; each needs owner decision 108 and root's
countersignature at a clean tree before the corresponding step may run, and none of them authorises
the read itself, which is a separate registration under protocol section 7 after Stage 3 closes.

## Stage-3 algorithm label (owner decision 101)

**`none`** -- the three preparations registered here are model-free / preparation cells that carry no
training-free RL operator. `configs/experiment/slurp-test-full-preprocess.json` is out of scope for
`scripts/checks/stage3_algorithm_label_check.py` (no `stage3` token in its stem or `experiment_id`,
and it names no Stage-3 spec relpath), exactly as the DEV-2000-ADDED preparation is, so the label
lives here as prose and needs no allowlist entry.
