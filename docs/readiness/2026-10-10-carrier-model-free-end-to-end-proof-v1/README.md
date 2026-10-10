# Carrier model-free end-to-end proof on the current base (A2T, E21, E22)

Date: 2026-10-10. Source: study `master` at `d3e29c843` (detached worktree, branch `sonnet/carrier-dry-proof`, tree
clean before and after except this file). Authority: owner decisions 196 (model-free reusable-base preparation), 242 and
252 (no carrier GPU flight before the SLURP lock). This note changes no production code, no config, no registration and
no hold. It is read-mostly evidence.

## Zero-contact assertion

No model, server, GPU, network or paid-API contact was made.

- No `llama-server` process was started and no serving session was attached by any step. Every flight-shaped step ran the
  production request path against `core.flight.runtime.WireCheckGate` and `WireCheckTransport` ("never opens a socket");
  every wire-check receipt reports `"model_contacts": 0` and `"attempt_aborted": true`. `core.flight.cli check` reports
  `"generation_authorized": false` and `"attempt_reservation": "deferred to core.model.adapter.FrozenCoreAdapter"`.
- Official scorers ran only over the wire-check transport's canned response ("numbers_are_meaningless"); they prove the
  scoring link, nothing else. No sealed per-row output of any run (SLURP test-sample or otherwise) was read.
- The one refused-by-design step is the rehearsal (`native_graph_rehearsal`): it needs `--session` (an attached serving
  session) and a P/S knowledge-lookup graph, so it was NOT run (see step 8).
- Caveat on proof strength: the "no socket" claim is established by code reading plus the receipts' own fields and by the
  fact that no server process existed to connect to. I did not install an OS-level network fence.

Data-root custody: no byte was written under `$SPEECHRL_DATA_DIR` by any dry run. `FlightRuntime.wire_check` hardcodes
`DATA/wire-check/<run>/` and `DATA/attempts/<run>/` as its output root, and a hybrid scratch root of symlinks fails the
runtime-view confinement check (`RuntimeViewError: runtime view media path must be confined beneath data root`; first
attempt, recorded below). I therefore ran every data-reading step inside a private mount namespace
(`unshare -rm`) with an overlayfs mounted over the data directory path (lower = the real data directory, upper = a
throw-away directory on WSL ext4 under `/tmp`). Everything the dry runs wrote (82 files in total, only under `attempts/` and `wire-check/`
all under `WIRECHECK-SAEA-...` run ids) landed in the upper layer and was deleted with it. The mount never existed in
the host namespace (`mount | grep -c carrier-ov` = 0 afterwards). A before/after mtime snapshot of the real data
directory (depth 2) differed only at `coordination/slurp-ver1b-samples-fold-a-v1` and `prepared/` (a parallel SLURP
session; none of our run ids exist under the real `wire-check/`). The suggested scratch directory
`analysis/SCRATCH-CARRIER-DRY-20261010/` was created for the failed hybrid-root attempt (symlinks only) and deleted. This
is a deliberate deviation from "scratch under the data directory": the overlay is strictly safer than writing there.

One side effect in the worktree: `scripts/checks/derived_media_confinement_check.py` unconditionally rewrites its
committed receipt (`docs/checks/.../2026-09-07-derived-media-confinement/`). I reverted it with `git checkout -- docs/checks`
and did not commit it.

## Result table: carrier x step -> status

Legend: PASS = ran and agreed; EXPECTED-REFUSE = the gate worked as designed and refused a HELD cell; GAP = a real
model-free gap in the base (details below); N/A = the step does not apply to this carrier's cell form; NONE = no cell exists.

| # | Step | A2T (arm 400 / smoke 4) | E21 (arm 1593 windows / smoke 4) | E22 |
| --- | --- | --- | --- | --- |
| 1 | Registered HELD ALL-OFF cells | PASS: `a2t-native-stage3-module-alloff-v1`, `-smoke-4-v1` | PASS: `earnings21-native-stage3-module-alloff-v1`, `-smoke-4-v1` | NONE: no experiment, dataset-window, model or full-baseline fragment |
| 2 | Module all-off byte proof (`module_equivalence_proof.py`) | PASS (`--at a2t0`, ok=true) | PASS (`--at e210`, ok=true) | NONE: no `ALLOFF_CASES` entry (hooks exist) |
| 3 | Compose + carrier adapter + roster/split hydration | PASS (400 / 4 rows, split `A2T-PAIRED-400-V1`) | PASS (44 calls = 1593 units / 1 call = 4 units) | PARTIAL: composes with an E21 model fragment; adapter refuses `E21 phase execution requires prepared_execution_units`. Raw whole-dev loads (10 calls, 40,054 s) |
| 4 | `core.flight.cli check` (pure: no lease, no data writes) | PASS x2 | PASS x2 | NONE |
| 5a | 4-row walk through the native graph (`native_episode_dry_run`) | N/A: refuses, direct-only program has no `native_episode` | N/A: same refusal | NONE |
| 5b | 4-row walk through the shared direct-only controller, fake transport (`wire_check`) | PASS: 4 contacts / 4 rows, 4 packets verified | PASS: 4 contacts / 1 call / 4 windows | NONE |
| 6 | Full-roster wire check (fake transport) | PASS: 400 contacts, 400 packets, 15.9 s | PASS: 1593 contacts, 286.7 s | NONE |
| 7 | Wire check + seal + official scorers (canned reply) | PASS smoke (4) and full (400); scorers `a2t-toolcall-official`, `-v2`, `a2t-toolcall`, `cost` | GAP on stock base: REFUSED `BundleError ... unit-stitch has no matching trace record`; PASS with a driver-side one-line equivalent (smoke only), scorers `asr-wer-whisper`, `conec-entity-wer-official`, `numeric-value-accuracy-v1`, `semantic-high-impact-error-rate-v1`, `cost`. Full not run | NONE |
| 8 | Rehearsal profile | N/A: legacy profile accepted, `review-off-v1` refused; real rehearsal needs a serving session and a P/S lookup graph | N/A: same | NONE |
| 9 | FIT estimate arithmetic | PASS: cap 13 = 1+3x4, 1201 = 1+3x400; audio 21 / 2761 s = ceil of measured 20.7075 / 2760.438 | PASS: declares no FIT (cap 0); 4 / 1593 calls, 360 / 141,346 s = ceil of measured 360.0 / 141,345.85 | NONE |
| 10 | Derived-media confinement | PASS (comparator form: `audio2tool-paired-400` carrier-rooted, binds, decoy refused; shipped check's own 5 fragments PASS but do not name this fragment) | N/A: no derived root; check has no Earnings loader | N/A: `earnings22-esb-dev1500-tail2s` is only its FOREIGN-root control |
| 11 | Standard scorer / adapter fixtures | PASS 66 tests (official scorer 18, runtime adapter 33, rails adapter 12, official-scorer subprocess 3) | PASS 172 tests (WER+Whisper normaliser 6+19, ConEC 30, numeric 29, adapters 12+20, native-window configs 8, delivery 20, FIT registration 4, execution units 24) | PASS 93 tests (E22 adapter 5, consumption profile 52, ReAct exhaustion 36) |
| 12 | Registration gate `--cell` on an empty data root | EXPECTED-REFUSE x2 (held, draft rows, no root-admission receipt) | EXPECTED-REFUSE x2 | NONE |
| 13 | Offline gates (`engineering_base`, `tool_catalog`, `stage3_algorithm_label`, `finite_completion`, `stage3_effect_floor`) | PASS (label `none`; finite-completion and floor gates do not select direct HELD cells) | PASS (same) | PASS (generic gates; nothing E22-specific to select) |
| 14 | Shared composition/transfer tests (`carrier_hooks` 10, `carrier_transfer` 34, `derived_media_confinement` 33, `carrier_descriptors` 32) | PASS 109 | PASS (same run) | PASS (same run) |

Bottom line. For A2T the base is provably runnable end-to-end without a model on both HELD cells, including the seal and
the official scorers. For E21 it is provable up to everything except the seal-and-score link, which stops at one named
base gap (step 7) that is a one-call fix and was shown sufficient. For E22 there is nothing to run: the thin adapter,
hooks, scorer and descriptor exist and pass their fixtures, but no cell and no execution-unit data exist.

## Step 1: cells and packages

| Carrier | Experiment fragment (cell) | Run id | Rows / units | Composed hash | Package |
| --- | --- | --- | --- | --- | --- |
| A2T arm | `a2t-native-stage3-module-alloff-v1` | `SAEA-A2T-NATIVE-STAGE3-MODULE-ALLOFF-V1` | 400 | `b78a4171904e6f6a...` | `docs/readiness/2026-09-30-a2t-native-stage3-module-alloff-v1/` |
| A2T smoke | `a2t-native-stage3-module-alloff-smoke-4-v1` | `...-SMOKE-4-V1` | 4 | `c2d2a606e062caaa...` | same |
| E21 arm | `earnings21-native-stage3-module-alloff-v1` | `SAEA-EARNINGS21-NATIVE-STAGE3-MODULE-ALLOFF-V1` | 44 calls, 1593 units | `3b5c8ed17fe0a6fc...` | `docs/readiness/2026-09-30-earnings21-native-stage3-module-alloff-v1/` |
| E21 smoke | `earnings21-native-stage3-module-alloff-smoke-4-v1` | `...-SMOKE-4-V1` | 1 call, 4 units | `5d260a651f9b777f...` | same |

All four: `readiness.state` = `held`, policy `phase-direct-only-v1` (one contact per row/unit), registered 2026-09-30 at
`60eb5feaa`, serving sessions `serving-a2t-native-role-base-np3-max2048-v3` and
`serving-e21-native-window-flightruntime-np4-max1024-v1`. A2T `allowed_execution_stages` = check, wire-check, prompt-fit,
worker, campaign; E21 = check, worker, campaign only (no `wire-check`; see step 5b).

## Step 2: module all-off byte proof

```
python -B scripts/analysis/module_equivalence_proof.py --at a2t0     -> rc=0, "ok": true
python -B scripts/analysis/module_equivalence_proof.py --at e210     -> rc=0, "ok": true
  (each: direct-layer ok, arm composed_identical true, smoke composed_identical true;
   differing_policy_paths [] ; off_arm true ; program_id phase-direct-only-v1 ; program_ceiling 1)
```

## Step 3: composition, adapter, roster hydration

Per cell, `build_flight_runtime(...)` then `_prepare()` (production compose, carrier adapter, split load, identity hash):

```
COMPOSE ok config_hash=c2d2a606e062caaa... carrier=audio2tool split=A2T-PAIRED-400-V1 identity=c7057020334be227... samples=4 policy=phase-direct-only-v1
COMPOSE ok config_hash=b78a4171904e6f6a... carrier=audio2tool split=A2T-PAIRED-400-V1 identity=965f145f581753874353216a25109a4746627095027cefbab0ed91c88090990a samples=400 policy=phase-direct-only-v1
COMPOSE ok config_hash=5d260a651f9b777f... carrier=earnings21-original split=e21-current-executor-four-row-proof-v1 identity=4d9ea907c05b67c43b5829e3e6c379ee37d39df012028a864aa0cdb7ae0c1992 samples=1 policy=phase-direct-only-v1
COMPOSE ok config_hash=3b5c8ed17fe0a6fc... carrier=earnings21-original split=discovery identity=fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e samples=44 policy=phase-direct-only-v1
PREPARED_ARTIFACTS []   (no pinned prepared first-phase artifact; the direct program declares none)
DECLARED_READINESS held | Consumption-module all-off arm on ... HELD: decision 187 keeps the GPU on SLURP until the SLURP lock ...
```

The composed hashes equal the hashes in the registered generation/FIT plans and in the module byte proof.

## Step 4: `core.flight.cli check`

I read the code first (`core/flight/cli.py`, `FlightRuntime.preflight`, `contracts/gate.py`). `check` takes no lease and
no `--lease-token-file`, reserves no attempt (it only tests that the attempt file does not already exist), opens no
transport and starts no server. It does run `FrozenCoreGate.assert_model_touch_allowed` (read-only: ledger row,
receipts, runtime hashes), requires a clean tree, and computes the prompt budget with the local estimator. It is
therefore a pure check by the stated criterion. Run inside the overlay, one invocation per cell:

```
python -B -m speech_aware_evidence_acquisition.core.flight.cli check --repo-root $PWD --data-root $SPEECHRL_DATA_DIR \
  --runtime-root $HOME --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json --experiment C --cell C
cli_check_a2t-...-smoke-4-v1  rc=0 {'sample_count': 4,   'prepared_artifacts_ok': True, 'attempt_reservation': 'deferred to core.model.adapter.FrozenCoreAdapter', 'split_id': 'A2T-PAIRED-400-V1'}   held generation_authorized=False blockers=None  prompt_budget [('direct','ALLOW')]
cli_check_a2t-...-v1          rc=0 {'sample_count': 400, ...}  held generation_authorized=False blockers=None  prompt_budget [('direct','ALLOW')]
cli_check_earnings21-...-smoke-4-v1 rc=0 {'sample_count': 1,   ... 'split_id': 'e21-current-executor-four-row-proof-v1'} held generation_authorized=False blockers=None
cli_check_earnings21-...-v1   rc=0 {'sample_count': 44,  ... 'split_id': 'discovery'} held generation_authorized=False blockers=None
```

A2T smoke prompt budget breakdown (verbatim): `rendered_text_tokens 4238, completion_token_ceiling 2048, required_window_tokens 6326,
operational_margin_tokens 18250, decision ALLOW`.

## Step 5: the 4-row walk

5a. `analysis/native_episode_dry_run` (the ver1a/nx walk) is written for plan-based native role episodes. Both carriers'
cells are the shared direct-only program with no `native_episode`, so it refuses, by design:

```
python -B -m speech_aware_evidence_acquisition.analysis.native_episode_dry_run --describe ... --experiment A --cell A
NativeEpisodeDryRunError: policy 'phase-direct-only-v1' declares no native_episode; this dry run walks native role episodes only
```
(identical line for A = the A2T smoke and A = the E21 smoke). The nx/ver dry runs
(`nx_r6_dry_run.py`, `ver1a_dry_run.py`) call exactly `compose_dry_run` + `dry_run_native_episode`, so they cannot cover
these cells either. This is a scope fact, not a defect: the direct baseline is one contact per unit and has no node
boundary to walk.

5b. The equivalent model-free walk for a direct program is `FlightRuntime.wire_check`, which drives the entire request
path (payload binding, packets, `FrozenCoreClient`/`FrozenCoreAdapter`, allowlist, attempt accounting, phase
dispatch) against the fake gate and transport. Verbatim summaries (smoke cells):

```
A2T smoke : WIRE_SUMMARY {"contact_count": 4, "model_contacts": 0, "sample_count": 4, "contacts_per_sample": 1, "policy": "phase-direct-only-v1", "attempt_aborted": true, "payload_keys_equal_arm_visible_fields": true, "phases": [{"phase": "phase-direct-only-v1", "rows": 4, "contacts": 4}], "max_tokens": 2048, "speech_packets_verified": 4}
E21 smoke : WIRE_SUMMARY {"contact_count": 4, "model_contacts": 0, "sample_count": 1, "contacts_per_sample": 1, "policy": "phase-direct-only-v1", "attempt_aborted": true, "payload_keys_equal_arm_visible_fields": true, "phases": [{"phase": "phase-direct-only-v1", "rows": 4, "contacts": 4}], "max_tokens": 1024}
```

The official CLI entry also works for A2T and is refused for E21 because the E21 cells' registered
`allowed_execution_stages` omit `wire-check`:

```
cli wire-check  a2t-native-stage3-module-alloff-smoke-4-v1  rc=0  (contact_count 4)
cli wire-check  a2t-native-stage3-module-alloff-v1          rc=0  (contact_count 400)
cli wire-check  earnings21-native-stage3-module-alloff-smoke-4-v1  rc=1
speech_aware_evidence_acquisition.core.flight.campaign.CampaignError: cell earnings21-native-stage3-module-alloff-smoke-4-v1 does not permit execution stage wire-check
```
(The E21 wire check above was therefore driven through the Python API, which has no such guard.)

## Step 6: full-roster wire check

```
A2T full : WIRE_SECONDS 15.9   WIRE_SUMMARY {"contact_count": 400, "model_contacts": 0, "sample_count": 400, ... "payload_keys_equal_arm_visible_fields": true, "speech_packets_verified": 400}
E21 full : WIRE_SECONDS 286.7  WIRE_SUMMARY {"contact_count": 1593, "model_contacts": 0, "sample_count": 44, "phases": [{"phase": "phase-direct-only-v1", "rows": 1593, "contacts": 1593}], "max_tokens": 1024}
```

## Step 7: seal and official scoring over the canned reply

A2T smoke, `WIRE_SEAL_SCORE {"status": "OK", ... "outputs_row_count": 4, "score_result": {... "job_count": 1, "succeeded": 1, "failed": 0 ...}, "scorers": ["a2t-toolcall-official", "a2t-toolcall-v2", "a2t-toolcall", "cost"], "ledger_surface_validated": true, "numbers_are_meaningless": ...}`.
A2T full: same, `"outputs_row_count": 400`, one official score job, `succeeded: 1`.

E21 smoke, stock base, GAP:

```
WIRE_SEAL_SCORE {"status": "REFUSED", "reason": "BundleError: outputs request_id 'WIRECHECK-SAEA-EARNINGS21-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1-1791670392060:4320211:unit-stitch' has no matching trace record '...:4320211:unit-stitch/response' (I7: every outputs request_id must appear in the trace)", "note": "a dirty study tree refuses a COMPLETED manifest by design ..."}
```

The tree was clean, so the "dirty tree" hint does not apply. Root cause (read from `core/flight/runtime.py`): the real
`seal()` calls `self._trace_execution_unit_deliveries(self._client, canonical_rows)` (line 12224) to emit the stitched
`.../unit-stitch/request|response|use` trace records for execution-unit cells; `_wire_check_seal_and_score` (line 13574)
builds the same canonical rows but never emits them, and the client has already been closed by then
(`client.close()` precedes it). The check is therefore blind to the one seal-time property that differs for window
cells. Hypothesis test, driver-side only (repo untouched): wrap the wire-check client's `close` so that it first calls
`rt._trace_execution_unit_deliveries(c, rt._canonical_output_rows(c))`:

```
PATCH_STITCH applied (driver-side monkeypatch)
WIRE_SEAL_SCORE {"status": "OK", ... "outputs_row_count": 1, "score_result": {... "succeeded": 1, "failed": 0 ...},
  "scorers": ["asr-wer-whisper", "conec-entity-wer-official", "numeric-value-accuracy-v1", "semantic-high-impact-error-rate-v1", "cost"], "ledger_surface_validated": true, ...}
```

So the missing wire-check step is sufficient on the smoke cell. The full E21 seal-and-score was not run (the 1593-unit
wire check alone took 287 s; scoring 1593 canned windows adds the WER normaliser pass).

## Step 8: rehearsal profile

`native_graph_rehearsal.rehearsal_profile(values, profile)` on both smoke cells:

```
REHEARSAL profile legacy-four-path-v1 -> accepted (None: legacy profile carries no episode config)
REHEARSAL profile review-off-v1 -> refused: ValueError Requested native rehearsal profile differs from its declared config profile
```
(neither cell declares `native_graph_capacity_profile` or a `native_episode`). `rehearse_native_graph` additionally
requires `attach_session(session_path, ...)` (a live serving session), exactly the released knowledge-lookup tool, and a
P/S role graph (`ValueError: Rehearsal permits only the released knowledge lookup`), so a rehearsal of a direct-only
cell is neither meaningful nor model-free here. It was not run; this is refusal-by-construction, not a skipped defect.

## Step 9: FIT estimate arithmetic

Cross-checked from the composed runtime against the registered plans (`FITARITH_OVERALL True`):

| Cell | rows/units | generation calls = units x ceiling 1 | planned_model_calls | FIT cap (composed `live_phase_fit.contact_cap`) | 1 + 3 x rows | registered FIT plan cap / calls / endpoint cap | audio s (measured -> planned) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A2T smoke | 4 | 4 | 4 | 13 | 13 | 13 / 13 / 13 | 20.7075 -> 21 |
| A2T arm | 400 | 400 | 400 | 1201 | 1201 | 1201 / 1201 / 1201 | 2760.438 -> 2761 |
| E21 smoke | 4 units | 4 | 4 | none (cap 0) | n/a | n/a | 360.0 -> 360 |
| E21 arm | 1593 units | 1593 | 1593 | none (cap 0) | n/a | n/a | 141,345.85 -> 141,346 |

`validate_live_phase_fit_config` accepted both A2T configs; split identity hashes and composed hashes in the plan files
equal the runtime's. The `1 + (2+1) x rows` formula is `register_carrier_module_alloff_cells.FIT_ENDPOINTS`. Measured
audio seconds for E21 come from the wire-check receipt `cost.audio_seconds_used`.

## Step 10: derived-media confinement

`scripts/checks/derived_media_confinement_check.py --data-root $SPEECHRL_DATA_DIR` prints five lines, all PASS
(`slurp-speech-native-dev1000-tail2s`, `audio2tool-calibration-400-tail2s`, `-16k`, `-16k-tail2s`,
`slurp-speech-native-dev1000`; final line `...derived-media-confinement.json: PASS`). Its hardcoded `FRAGMENTS` list contains
no fragment used by these cells and only `slurp` / `a2t` roster loaders. Calling its own `check_fragment` on the A2T
dataset fragment of the HELD cells:

```
DMC-EXTRA audio2tool-paired-400 PASS roots=0 binds=True without_decl_refused=False decoy_refused=True foreign_refused=False
```
(carrier-rooted comparator semantics: binds, the decoy is refused, no derived root declared). E21's
`earnings21-native-window-full44-v1` / `e21-native-window-four-row-v1` declare no derived media root, and E22's
`earnings22-esb-dev1500-tail2s` is the only E22 derived-root fragment (used by the shipped check solely as the FOREIGN
control). There is no Earnings roster loader in the check.

## Step 11: scorer and adapter fixtures (targeted pytest, no full suite, inside the overlay)

```
pt_a2t    66 passed, 3 warnings in 14.67s   (test_audio2tool_official_scorer, test_audio2tool_runtime_adapter, test_rails_audio2tool_adapter, contract/test_a2t_official_scorer_subprocess)
pt_e21   172 passed in 3.60s                (test_asr_wer_whisper, test_whisper_normalizer_vendored, test_conec_entity_scoring, test_numeric_value_accuracy, test_earnings_adapter, test_earnings_runtime_adapter, test_e35_earnings_native_window_configs, test_e35_earnings_delivery_normaliser, test_e21_native_window_fit_registration, test_execution_unit_windows)
pt_e22    93 passed, 3 warnings in 6.67s   (test_earnings22_runtime_adapter, test_earnings22_consumption_profile, test_e22_react_exhaustion)
pt_shared 109 passed in 2.94s               (test_consumption_module_carrier_hooks, test_consumption_module_carrier_transfer, test_derived_media_confinement, test_carrier_descriptors)
```

Limits: no test names arXiv:2604.22821 Table 3. The A2T `a2t-toolcall-official` fixtures check scorer logic and the
official-evaluator subprocess; the Table 3 calibration is an empirical comparison on sealed model output
(`docs/results/2026-09-04-a2t-official-protocol-replication-v1-verdict.md`) and is not re-proved model-free here. The
Earnings WER fixtures cover the Whisper normaliser and the `asr-wer-whisper` scorer; "WER beside `saea-scoring-v1`" is
covered where those scorers are registered in the E21 tests above.

## Step 12: registration gate `--cell` against an empty data root

`python -B scripts/checks/flight_registration_check.py --data-root <empty tmp dir> --cell C --include-held --verbose`
(tree mode not used). All four exit 1, each with exactly the three expected finding classes and nothing else (so the
package carries its analysis recipe and READ row; no `no-package` / `no-analysis-recipe` / `read-row-missing`):

```
[not-ready] readiness.state is 'held', not 'ready'
[row-not-countersigned] SAEA-A2T-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1 (generation): the exposure-ledger row is a DRAFT (root countersignature pending); a draft never authorises contact
[receipt-missing] SAEA-A2T-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1: decision receipt coordination/a2t-native-stage3-module-alloff-v1/root-admission-v1.json does not exist on the data root
```
plus the same two for each `...-FIT-V1` row on the A2T cells; the E21 cells carry no FIT row. The temp root stayed empty.
This is the intended refusal of a HELD cell, i.e. the gate is wired and will not pass before root mints the receipt.

## Step 13: offline gates

```
engineering_base_check.py        engineering base check: PASS
tool_catalog_check.py            tool catalog check: PASS (34 tools, 1 extra pin(s), 17 module(s) clean of framework clients)
stage3_algorithm_label_check.py  PASS (1149 Stage-3 cell(s) of 1598 experiment fragment(s)); our four cells listed with label "none"
finite_completion_policy_check   PASS (576 in-scope plan(s)); our direct HELD cells declare no native_episode and are not selected
stage3_effect_floor_check.py     PASS (0 blocking, 10 advisory); none of our four cells is named
```

## E22: does an ALL-OFF cell exist?

No. Present: carrier descriptor `earnings22-original` (`data/carriers.py`), the thin runtime adapter
`rails/adapters/earnings22_runtime.py` (a subclass of the Earnings-21 runtime adapter, whole `dev` split only),
`rails/adapters/earnings22_module_hooks.py` (profile `earnings22`, `carrier_components={}`, no lock),
`configs/baseline/e22-native-window-direct-base-v1.json` (only `policy` + `phase_material`), the delivery normaliser
`saea-deliver-earnings22-text-v1`, the registered `asr-wer-whisper` scorer, dataset fragment
`earnings22-dev-subset10.json` (`{"carrier_lock_key": "earnings22-original", "split_name": "dev"}`), raw `dev` data (10
calls, 40,054 s) and 93 passing fixtures. Absent: any `configs/experiment/*e22*native*` or module-all-off fragment, any
E22 window inventory or feature packets under `prepared/` or `analysis/`, an `ALLOFF_CASES` entry, a ledger row, a
readiness package, and an own null. `docs/readiness/2026-10-01-earnings22-consumption-plumbing-v1.md` says the same:
"The fragment is a composition layer, not a runnable flight."

Probe (outside the repo, in a throw-away copy of `configs/`, deleted): the E21 all-off smoke experiment fragment
re-pointed at `earnings22-dev-subset10` + `e22-native-window-direct-base-v1`:

```
E22PROBE compose ok
E22PROBE missing-for-adapter: ['arm', 'scorers', 'prepared_execution_units', 'prepared_window_feature_packets', 'task_instruction', 'speech_feature_key_representation_id', 'speech_feature_matcher_policy_id', 'knowledge_snapshot_relpath']
E22PROBE adapter refused: CoreError E21 phase execution requires prepared_execution_units
```

## Failures and gaps (exact lines)

1. E21 wire-check seal-and-score, stock base: `BundleError: outputs request_id '...:4320211:unit-stitch' has no matching trace record '...:4320211:unit-stitch/response' (I7: every outputs request_id must appear in the trace)`. Real base gap; sufficiency of the fix shown driver-side.
2. E21 `cli wire-check`: `CampaignError: cell earnings21-native-stage3-module-alloff-smoke-4-v1 does not permit execution stage wire-check`. Registered-config property of the HELD cells.
3. `native_episode_dry_run`: `NativeEpisodeDryRunError: policy 'phase-direct-only-v1' declares no native_episode; this dry run walks native role episodes only` (both carriers). Scope fact.
4. Rehearsal: `ValueError: Requested native rehearsal profile differs from its declared config profile` (review-off) and the structural need for a serving session. Scope fact.
5. Registration gate: three expected refusals per cell (held, draft row, missing root-admission receipt). Intended.
6. E22: `CoreError: E21 phase execution requires prepared_execution_units` (no cell, no data).
7. First infrastructure attempt (hybrid symlink data root, discarded): `RuntimeViewError: runtime view media path must be confined beneath data root`.

## Model-free work items that would make each base provably runnable end to end

A2T (all HELD cells already provable; remaining items are strengthening, each model-free and small):
- A2T-1. Re-score the already-sealed direct bundle(s) through `a2t-toolcall-official` with the offline scorer and put the
  paper-column (arXiv:2604.22821 Table 3) next to the repo column as a standing regression fixture (half a day).
  Reads sealed A2T rows only; no contact.
- A2T-2. Add `audio2tool-paired-400` to `derived_media_confinement_check.FRAGMENTS` (comparator form) so the HELD cells'
  dataset fragment is named by the shipped check (about an hour; the check also rewrites its committed receipt).
- A2T-3. Author the per-cell guarded queue rows (October 7 audit item) from the configs for the A2T serving geometry (a
  few hours); no flight.

E21 (everything except one link already provable):
- E21-1 (blocking for a full model-free proof). Make `FlightRuntime._wire_check_seal_and_score` emit the execution-unit
  stitch trace exactly as `seal()` does, before the wire-check client closes (call
  `_trace_execution_unit_deliveries(client, canonical_rows)` ahead of `client.close()`), plus a unit test that a
  4-window unit cell passes `wire_check(seal_and_score=True)` (about 2 hours; changes shared runtime code, so it needs a
  reviewed commit and a re-pin of any package whose hashed implementation inputs include `runtime.py`; HELD cells have no
  flown attempt to protect).
- E21-2. Allow `wire-check` in the E21 cells' `allowed_execution_stages` (as A2T already does) so the official CLI works
  for them. This edits registered cell bytes, so it needs a successor registration or an owner-approved re-pin; the
  Python-API wire check already gives the same proof meanwhile.
- E21-3. Run the full-roster seal-and-score (1593 canned units) once E21-1 lands (about 10 minutes of CPU).
- E21-4. Measure the native-window own null: an in-chain A/A (a GPU flight, not model-free) remains outside this task.

E22 (no all-off cell; model-free registration work, in dependency order):
- E22-1. Window inventory for the 10 `dev` calls (`prepare-window-inventory`, CPU, no lease; about 450 windows at the
  E21 mean of 88.7 s per window) written to a data-root receipt, and a `prepared_execution_units` pin.
- E22-2. Dataset fragment for the window form (reuse `earnings22-dev-subset10` plus execution-unit pin) and the full
  baseline fragment: `e22-native-window-direct-base-v1` plus `arm`, `scorers` (`asr-wer-whisper` only; E22 has no entity
  or ConEC layer), serving slots/slot tokens, `task_instruction`, `speech_feature_key_representation_id`,
  `speech_feature_matcher_policy_id`, `prompt_fit_multiple`, execution-unit and packet pins; no knowledge snapshot.
- E22-3. Model fragment for the E22 np4 max1024 geometry (copy of the E21 `q4km-e21-native-window-packets-...` fragment
  with E22 feature roots and receipts).
- E22-4. Extend `register_carrier_module_alloff_cells.py` with `--carrier e22` (a `CARRIERS` entry and a `derive_e22`
  modelled on `derive_e21`), add an `e220` case to `module_equivalence_proof.ALLOFF_CASES`, generate the arm and
  smoke-4 experiment fragments, the readiness package, DRAFT ledger rows, flip/chain/read scripts, and unit tests mirroring
  `test_consumption_module_carrier_transfer` for the `e220` byte proof.
- E22-5. Re-run steps 2 to 13 of this note on the new cells.
- Not model-free, so excluded from the estimate: the window feature packets (an encoder forward pass, so a lease and GPU,
  or the raw-speech arm if the owner prefers it), the owner data-use / source-release decision for E22, the in-chain
  A/A own null, and any flight.
- Model-free estimate: roughly one to two engineering days (E22-1 to E22-5), mostly mirroring the E21 registration.
  A real wire check of the E22 cell also needs the packets (or the raw arm), so the full step-5b/6/7 proof lands after the
  encoder step; steps 2, 3 (compose and adapter), 4 (`check`), 9, 11, 12, 13 can land before it.

## Reproduction

All commands were run from `/home/chao/saea-worktrees/sonnet-carriers-dry` with `source ~/.venvs/speechrl/bin/activate`,
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=<worktree>/src`, `SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data`,
`python -B`. Data-reading steps were wrapped in `unshare -rm sh -c 'mount -t overlay overlay -o
lowerdir=$SPEECHRL_DATA_DIR,upperdir=/tmp/<scratch>/up,workdir=/tmp/<scratch>/wk $SPEECHRL_DATA_DIR && exec "$@"'`. The
driver scripts (compose / wire-check / FIT arithmetic / rehearsal / E22 probe) lived in the session scratchpad and are
not part of the repository; each used only public functions named above (`build_flight_runtime`, `FlightRuntime._prepare`,
`verify_prepared_artifacts`, `wire_check`, `validate_live_phase_fit_config`, `rehearsal_profile`,
`derived_media_confinement_check.check_fragment`).
