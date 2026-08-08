# P1 engineering scaffold — Audio2Tool tool-calling baseline through the gated driver (2026-08-08)

Status: ENGINEERING COMPLETE, model-free. No model was run, no network was
touched, no dataset audio bytes were read (metadata manifests and the
tools registry CSV only). The frozen scoring package
(`src/speech_aware_evidence_acquisition/scoring/`, E0 D3) is untouched;
`docs/datasets.lock.json` (umbrella) is untouched.

## What was built

One experiment = config + registered components, per the anti-fragmentation
contract. Every piece below is unit-tested against a synthetic
`Audio2ToolWorld` (`tests/unit/conftest.py`) that mirrors the real on-disk
layout and the real observed gold shapes; nothing depends on real data.

| piece | where | role |
|---|---|---|
| gold parser | `reproduction/toolcall_gold.py` (`a2t-gold-v1`) | manifest entry -> `ToolCall` tuple; call-string vs bare-name vs concatenated shapes; JSON-coercion of stringified params |
| carrier loader | `data/audio2tool.py`, registered `audio2tool` in `core/carriers.py` | frozen-receipt-scoped `SampleRef`s; receipt hash re-verified; per-item `query_idx` cross-check; wav-header `sample_rate_hz`; manifest `duration` -> `audio_seconds` |
| scorer-side gold | `data/audio2tool.py::load_expected_calls` | the ONLY gold egress; never on the runtime path (D2) |
| probe-split seam | `reproduction/probe_split.py` + dispatch in `core/split_receipt.py` | any non-contract split name resolves `docs/receipts/probe-samples/<name>.json` into a `VerifiedSplit` |
| instruction seam | `core/instructions.py` + `INSTRUCTION_FILLS` in `core/base.py` + resolution in `core/driver/run.py` | frozen template + registered fill (`audio2tool-tool-schemas` renders the full `tools_registry.csv`); literal `task_instruction` unchanged |
| scorer | `reproduction/a2t_scorer.py`, registered `a2t-toolcall` in `core/scorers.py` | P0 metric trio + `per_tier` breakdown; echoes `a2t-scorer-v1` + `a2t-gold-v1` into the aggregate |
| configs | `configs/dataset/audio2tool-r1-sample400.json`, `configs/baseline/a2t-direct.json`, `configs/experiment/r1-audio2tool.json` | the four-fragment composition (model fragment reused: `qwen3-omni-llamacpp`) |
| tests | `tests/unit/test_toolcall_gold.py`, `test_audio2tool_loader.py`, `test_probe_split.py`, `test_instructions.py`, `test_a2t_scorer.py` | 91 new tests incl. a full `run_experiment` end-to-end over the probe split with a fake transport, and pre-flight checks over the REAL committed receipt + fragments |

Identity conventions (decision to review):

- `sample_id` = `"{tier}:{id:06d}"` (e.g. `tier1_direct:000045`); carrier
  `audio2tool`; `speech_ref` = `audio2tool/tier1_direct:000045`.
- **Two split hashes, on purpose.** The receipt's own `split_identity_hash`
  (`e1d751e6…`) is over colon keys (`audio2tool:tier1_direct:000045`) and is
  re-verified fail-closed at every resolution (probe manifest binding). The
  `VerifiedSplit.identity_hash` the ExecutionPlan/run manifest carry is
  DERIVED under the E0 slash convention (`data.splits`), because
  `core.bundle.verify_bundle` independently recomputes exactly that
  convention from manifest carrier + bare ids. Same frozen item set, two
  serializations; `saea-driver smoke` derives the plan hash itself via
  `load_split`, so no operator ever computes either by hand.

## Data facts verified this session (metadata only)

- Tier manifest fields: `id`, `tier`, `query_idx`, `query`, `domain`,
  `category`, `tool_id`, `tool_name`, `expected_tool_call`,
  `extracted_params`, `functions`, `instruction`, plus per-tier extras
  (`additional_tool_calls`/`path`/`duration`/`speaker_*` absent on tier7;
  tier7 adds `user_request`/`chat_history`; tier6 adds
  `original_tool_call`/`correction_type`; 821 items carry `background_*`).
- **Ground truth** = `tool_name` (clean primary name) + `expected_tool_call`
  (call-string or bare name; sometimes domain-dotted) + `extracted_params`
  (string-typed, sometimes JSON-stringified, sometimes INCOMPLETE — tier5
  id 2007) + `additional_tool_calls` (bare names, call-strings, or
  CONCATENATED call-strings in one element — tier3 id 2560).
- All 557 gold call names over the 400 receipt items resolve in
  `tools_registry.csv` (152 rows, unique `tool_id`). Item-level
  `tool_id`/`functions` metadata can disagree with `tool_name` (tier1 id 1:
  `tool_id` 70 = `setLightState` in the registry, gold `setLighting` =
  registry id 115) — the loader ignores `tool_id`/`functions` for identity.
- All 400 receipt items exist in the manifests with matching `query_idx`;
  the 50 tier7 items all have `path: null` — audio is per-turn in
  `chat_history` (`turn_XX_{role}_… .wav` under `query_{id:05d}/`).
- `tools_registry.csv` lives at the ASSET ROOT (`datasets/audio2tool/`),
  not under `public/`.

## Remaining gaps (exact list)

1. **Umbrella lock entry `audio2tool` (owner amendment; THE blocker).**
   Everything fails closed on exactly this today: loader
   (`AssetResolutionError: asset 'audio2tool' not found`), the model-touch
   gate (`_resolve_carrier_dataset_entry`), and the scoring entry gate. The
   gates read `kind: dataset` entries from the lock's `datasets` /
   `asset_catalog` lists and require `profiles` intersecting
   `{speech-aware-core, -secondary, -diagnostics, -small-public}`. Draft
   entry (fields the study gates actually read, plus provenance to fill at
   amendment time):

   ```json
   {
     "name": "audio2tool",
     "kind": "dataset",
     "local_subdir": "datasets/audio2tool",
     "profiles": ["speech-aware-secondary"],
     "lifecycle": "STAGE2_CANDIDATE",
     "license": "disk README CC-BY-NC-4.0 vs paper CC-BY-4.0 — owner decision pending (R1 re-plan decision 3)",
     "source": "<exact HF repo id + revision from the .hfd receipt — fill at amendment>",
     "verification": {"tier_manifests": 8, "items_total": 30733, "tools_registry_rows": 152}
   }
   ```

2. **D1 media-identity coverage (second gate-visible gap — E0 authority,
   not fixable from this repo's code).** `FrozenCoreAdapter` construction
   calls `gate.verify_media_identity("audio2tool", …)`, which requires
   per-sample `(bytes, sha256)` records in
   `docs/receipts/artifacts/d1-identity.json` — that artifact has no
   `audio2tool` carrier, and it is itself hash-pinned by the E0 closure
   receipt, so extending it requires an owner-approved D1
   amendment/regeneration (hash the 400 receipt wavs only, mirroring the
   split-scoped check). Also verify then: wav bitrate must sit in the gate's
   4–512 kbps plausibility band (16 kHz mono 16-bit PCM = 256 kbps fits;
   44.1 kHz stereo would NOT — format unverified, no audio bytes read).
3. **`sample_rate_hz` from wav headers is unverified against real data.**
   The loader reads it via the stdlib `wave` module (unit-tested on
   synthetic PCM wavs). If any real file is non-PCM, the loader fails
   closed; first real load will tell.
4. **Tier3/tier8 bare additional calls have no argument record** anywhere in
   the manifests -> gold arguments `{}` -> Slot-F1/Exact-Match on those
   tiers are depressed relative to whatever the paper's unreleased eval
   did. Recorded interpretation risk on top of the already-accepted
   a2t-scorer-v1 reimplementation risk; Tool Accuracy (the published tier
   rows) is unaffected.
5. **Tier7 protocol fidelity.** The scaffold sends only the FINAL user
   turn's wav; prior user/agent turns are dropped (bare-core `history` is
   D2-visible but hard-wired `[]` in `core/policies.py`). Options when P1
   results matter for tier7: (i) plumb past turns through `history`
   (policies+adapter work, D2 field already exists), (ii) owner-approved
   derived concatenated wavs with their own identity receipts, (iii) accept
   and report tier7 as a separate, caveated row. Tier rank-order over the
   other 7 tiers is unaffected.
6. **Prompt fidelity vs the paper** (already accepted in the plan §P1): our
   frozen template `configs/probes/r1_audio2tool_direct.txt` + full-registry
   `{tool_schemas}` fill is a reconstruction; the paper's exact prompt is
   unreleased. A per-item `functions`-based fill can register later as a new
   `INSTRUCTION_FILLS` entry + new frozen template without touching wiring.
7. **Operational (not code):** owner P1 authorization (plan decision 5),
   exposure-ledger pre-registration + `ExecutionPlan` + fresh attempt id
   (all produced by `saea-driver smoke`), session receipt for the
   receipt-pinned llama-server, and `planned_speech_audio_seconds` (sum the
   400 `duration`s at run prep; not computed this session — no data pass).

## Operator invocation (after gaps 1–2 + authorization)

WSL2 (`Ubuntu-24.04`, `~/.venvs/speechrl`), llama-server resident per the
R0 smoke runbook, then one command:

```bash
saea-driver smoke \
  --model qwen3-omni-llamacpp \
  --dataset audio2tool-r1-sample400 \
  --baseline a2t-direct \
  --experiment r1-audio2tool \
  --run-id SAEA-E-002-p1-a2t \
  --execution-profile baseline-reproduction \
  --planned-model-calls 400 \
  --planned-gpu-hours <estimate> \
  --planned-speech-audio-seconds <sum of the 400 durations + margin> \
  --run-dir "$SPEECHRL_DATA_DIR/runs/saea-e-002" \
  --runtime-root <llama.cpp runtime root> \
  --tracking-uri <local mlflow uri>
```

`smoke` resolves the probe split (`r1-audio2tool-sample`) through the same
verified `load_split` path, derives the plan/protocol hashes itself, runs
gate-enforced, and finalizes: `verify_bundle` -> `score_bundle` runs
`a2t-toolcall` + `cost` -> per-tier rows land in the scores artifact for
the pre-registered success check (tier rank order; per-tier |delta| <= 5pp
vs the published Qwen-3-Omni-30B rows).

## Test status (this machine, Windows worktree, main checkout's venv)

`789 passed, 30 skipped`; remaining failures are the KNOWN pre-existing
environment set only: `tests/unit/test_llama_server_transport.py` (14,
spawned-process liveness on this Windows host), one session-liveness flake
(`test_attach_refuses_pinned_binary_process_not_listening_on_claimed_port`),
and `tests/contract/test_cli_module_dispatch.py::test_module_score_outputs_…`
(umbrella lock path does not resolve from a nested `.claude/worktrees/`
checkout — layout artifact, passes in the canonical checkout location).
