# Earnings21 native window registration preparation

Status: CPU-prepared and held. This directory and its additive configuration fragments grant no model, tokenizer, ASR, scorer, encoder, service, or GPU contact. Root must complete stable-source admission and the exposure ledger before the first contact. The original held configuration and its readiness evidence remain unchanged.

## Frozen comparison

The comparison remains the approved 44-call, 1,593-window direct/system pair. Both arms retain split identity `fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e`, the existing feature-window protocol, decoder-only Q4_K_M geometry `-c 98304 -np 4`, four slots of 24,576 tokens, maximum output 1,024, temperature zero, and seed 20260915.

The direct arm keeps one direct contact per window. The system keeps Perception once and up to two rounds of Solver once, Reviewer three times, and Planner once: at most eleven core contacts per window. Its two ConEC stores remain call-scoped and Solver-only. Reviewer alone may request the existing bounded local CPU Whisper span. Planner emits ACCEPT or REVISE, at most one revision is allowed, and Solver alone supplies the final transcript.

The existing arm ceilings are unchanged:

| Arm/contact family | Calls | GPU hours | Speech seconds |
|---|---:|---:|---:|
| Direct generation | 1,593 | 4.0 | 141,346 |
| Direct static request fit | 4,780 endpoints | included in the direct 4.0 | same direct envelope |
| System generation | 17,523 | 24.0 | 1,554,805 |
| System realized native fit | 70,092 endpoints | included in the system 24.0 | same system envelope |
| Reviewer CPU ASR | 6,372 | CPU protocol; existing plan schema ceiling 0.001 | 190,257 |

The fit rows do not add GPU-hour allowances to either arm. Ceilings are not targets.

## Additive configuration

The original held experiment and baseline fragments are not edited. The additive direct experiment contains the fit cell and generation cell in one fragment so their model-visible configuration stays identical. The reserved direct baseline is currently byte-identical to the original direct baseline; after the fit seals, its only permitted content change before final generation registration is the `prepared_request_fit` binding plus any separately reviewed metadata that does not enter model requests.

- `configs/experiment/e21-native-window-direct-full44-registration-v1.json`: held direct fit and original direct generation identities.
- `configs/baseline/e21-native-window-direct-full44-registration-v1.json`: reserved final direct baseline; no fit receipt is claimed yet.
- `configs/experiment/e21-native-window-context-tools-full44-registration-v1.json`: held system derivative with the original system generation identity and existing native-fit identity.
- `configs/campaign/e21-native-window-direct-vs-context-tools-full44-registration-v1.json`: ordered direct then system generation. Both cells remain held, so the campaign cannot run.

The fit cell already declares `prompt-fit` as a structurally valid stage to avoid changing the fit input configuration after registration. This stage declaration is not contact authority: no fit exposure row exists, and the shared gate requires a unique `consumed=no` exposure row before tokenizer access. Generation cells declare `campaign` but remain held, so campaign readiness refuses them.

Current CPU-preparation hashes are provisional registration inputs, not final generation pins:

| Item | SHA-256 |
|---|---|
| Direct registration experiment bytes | `f39c960500919e32e6a6d8f47c644505e672365b43ff6883347b80b36990aa99` |
| Direct reserved baseline bytes | `22f82fe43024fac92ee3569a7d93da01730dd4ddfd6f509c5c9dec0b7bfae08c` |
| Direct composed configuration | `ab43b870ecc8471b44f9ba1d13cc59e0f3752bec73b0e67f262d9bd74affd0f1` |
| Direct composed protocol | `a89a38f5e6960794c2f7ce642be8ab305d40d4dfcef1f40d454c45b6b344e9e1` |
| System registration experiment bytes | `a753cafdc4af345e5462bb5adc523da6cdf382936ef9aca6300cdb3315b0b4fb` |
| System composed configuration | `6b1b24c9d49d2e91645ab1aa5178dde217997ac549d2055c060038e6debd6a80` |
| System composed protocol | `f70d04ad408f0d802ce826ad90b151a24f8c084e28b8acd1c3eeb78f32077f6e` |
| Ordered campaign bytes | `6a0b7366f3020c7f055056dede2bdcc9ba80e1322a1503230cf4dd99a770eee8` |

The four adjacent plan drafts record these provisional protocol values. The ASR plan, protocol, runtime inventory, output namespace, and bounds remain the existing pins under `docs/readiness/2026-09-15-e21-native-window-system-v1`; this preparation does not replace or rewrite them.

## Static fit identity and receipt contract

The supported direct fit identity is fixed as:

- run: `SAEA-E21-NATIVE-WINDOW-DIRECT-FULL44-FIT-V1`;
- attempt: `attempt-e21-native-window-direct-full44-fit-v1`;
- output: `prepared/SAEA-E21-NATIVE-WINDOW-DIRECT-FULL44-FIT-V1/attempt-e21-native-window-direct-full44-fit-v1/request-fit.json`;
- contact cap: `1 + 3 * 1593 = 4780` tokenizer/template endpoints;
- generation contacts: zero.

The shared static path first materializes every actual direct request through `FlightRuntime.materialize_phase_requests`. For an execution-unit roster it requires exactly 1,593 requests, resolves each scoped contact to its registered `ExecutionUnit`, validates the parent, source slice, duration and prepared feature packet, and restores canonical `request_key` order.

The fit artifact input binds:

- a configuration digest that excludes only preparation receipt fields and per-cell readiness;
- the discovery split identity;
- the normalized model-visible request boundary, excluding only request routing ID and serving slot ID;
- the full runtime receipt and required resident identity;
- the exact execution-unit inventory declaration and roster content hash;
- the prepared window feature-packet declaration;
- canonical source-window records;
- hashes of the runtime, transport, fit, configuration, adapter, core-client, speech-feature, packet and window-request implementations.

The final generation preflight re-materializes the same requests and requires the pinned artifact hash, identical input binding, `every_request_fits: true`, exactly 1,593 successful rows, and the complete ordered execution-unit `request_key` roster. Adding this artifact's own `prepared_request_fit` pin does not change the artifact input digest because that field is explicitly excluded to break self-reference. Readiness changes are also excluded. Every other configuration or source change invalidates the receipt.

Do not modify the experiment cell roster, allowed stages, model, dataset, task prompt, decoding, feature packets, execution-unit inventory, source windows, implementation, or serving identity between the registered fit and final generation. If any of those change, discard this pending generation registration and perform a new root-reviewed registration before contact.

## Acyclic finalization sequence

1. Root records stable-source scientific admission over the intended fit and generation identities, behavior, source evidence and arm ceilings. Do not bind future final configuration, protocol or source-freeze hashes inside a decision whose own hash will enter readiness.
2. Bind the admission in the fit cell readiness and finalize all non-receipt configuration metadata before fitting. Derive the exact direct-fit plan and append its unique unconsumed exposure row. The shared static preparation authorization replaces the experiment's generation call count with the explicit 4,780-endpoint cap for the distinct fit run; the same experiment fragment is intentional.
3. Freeze the completed fit configuration, plan, ledger and implementation source last. Run the registered static fit once through the shared coordinator, matching root service and exclusive lease. Stop on failure and preserve its contact journal and source checkout.
4. Validate the complete fit artifact. In a separate final-generation checkout with identical implementation, add its data-relative prepared_request_fit path/hash to the reserved direct baseline, its preparation requirement to direct readiness, and the existing root decision requirement to both generation cells. Promote the generation readiness before deriving final generation hashes. Only receipt/readiness fields may change from the fitted configuration.
5. Recompute final direct and system composed hashes and runtime protocols, finalize both generation plans and the system native-fit plan, and append their exact exposure rows. Register the unchanged CPU ASR ExecutionPlan under its existing protocol and source pins. Preserve the completed direct-fit plan, row, artifact and checkout.
6. Verify all final plan, exposure, decision and preparation bindings; freeze the final generation source last. Do not issue another decision or edit readiness after this freeze. Root then runs the committed direct-then-system campaign in the same service process used for the fit.
7. After both arms and their first complete official scores seal, root registers and binds the paired quality release before opening task outcomes. Retain per-sample evidence and do not repeat the official scorer.

No final generation hash is claimed by this preparation. The direct generation hash changes after receipt/readiness binding even though the shared static-fit input normalization preserves request equivalence. Draft generation, native-fit and ASR exposure rows remain outside the live ledger until their exact final plans exist.

## Fixed source pins

The registration continues to consume the original source bindings:

- execution units: `analysis/SAEA-E21-DR-SHARED-EXACT-WINDOW-INVENTORY-V1/window-inventory.json`, schema `saea-prepared-artifact-v1`, SHA-256 `7b12a5c32654855701c48b57152ab1643e0c776b9a7a3853fda009a6ac78face`;
- feature packets: `analysis/SAEA-E21-DR-FULL-WINDOW-GPU-ENCODING-V1/window-feature-packets.json`, schema `saea-prepared-artifact-v1`, SHA-256 `9aba4ff0d9a78dc66afcdf73f35bea0e7e6919e8448211f383f95219833a5115`;
- model fragment: `configs/model/q4km-e21-native-window-packets-cddb000c-np4-max1024-v1.json`, SHA-256 `408da6e61f5fd0f62e24f3211bbaf7e37b59bb7621d046cc7d7575d13633b1e1`;
- decoder runtime receipt: `docs/receipts/runtime-q4km-e21-feature-inference-cddb000c-v2.json`, schema `saea-runtime-receipt-v3`, SHA-256 `a472219e12fd2a3d08446c29ecf5273646832990fd0379cba380c702b111aba2`;
- analysis plan: `docs/readiness/2026-09-15-e21-native-window-system-v1/analysis-plan.json`, SHA-256 `d498ecbb637d5b19e7a031d36cff6d012cb208c2ca1f054148e14d1362568087`;
- ASR plan: `docs/readiness/2026-09-15-e21-native-window-system-v1/live-asr-execution-plan-v1.json`, SHA-256 `9a374d7569795a853594c1b96788756b6ed2fc3e9fafe339ca3f3d3335143ffc`;
- ASR protocol: `prepared/SAEA-E21-NATIVE-WINDOW-SPAN-PROTOCOL-V1/protocol.json`, schema `saea-local-whisper-decode-v1`, SHA-256 `566f35df0b3780bfab347726e637065c94c2e3fc8a33abfeafd342895011a112`;
- ASR inventory: `prepared/SAEA-SLURP-NATIVE-SYSTEM-LIVE-SPEECH-PREPARE-V1/full-runtime-inventory-v2.json`, schema `saea-local-whisper-runtime-inventory-v2`, SHA-256 `e5e6d37646438ab57bb3362ced18726cde4f2762a2893f7e6a416e7e484d0427`.

The system store releases and semantic snapshot identities remain exactly those in `configs/baseline/e21-native-window-context-tools-full44-v1.json`. No automatic retrieval, new store, raw-only fallback, new screening population, or new scientific variant is introduced.

## Model-free validation

Run only after checking out the exact preparation commit and setting `SPEECHRL_DATA_DIR` to the existing source root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /home/chao/.venvs/speechrl/bin/python -B -m pytest -q \
  tests/unit/test_e21_native_window_system_config.py \
  tests/unit/test_execution_unit_static_fit.py \
  tests/unit/test_flight_campaign.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /home/chao/.venvs/speechrl/bin/python -B \
  scripts/checks/engineering_base_check.py
```

Also compose both additive experiments and load the ordered campaign in a CPU-only check that asserts: original generation IDs, distinct direct-fit identity, held readiness, direct cap 1,593, fit cap 4,780, system cap 17,523, native fit cap 70,092, population 44/1,593, matching split, and unchanged task, source, model, analysis and ASR values. These checks establish configuration consistency only. They do not establish contact admission, capacity, scoring, or task quality.
