# Status 017: G2 closed; exemplar gate failed; E21 preparation continues

Date: 2026-09-10 UTC. Supersede STATUS-016 as a coordination snapshot; preserve all prior snapshots and sealed artifacts.

## Completed GPU work and service state

G2 N and twin each completed 1,000 generations and one complete official aligned scoring job, both FINALIZED. They used the same session `slurp-g2-kus4n-aligned-np8-20260910-root`, PID 3092, and frozen worktree `/home/chao/saea-worktrees/g2-kus4n-runtime` at c45941547f2a47aac70bf54c1167c066ae2a4d9a. Both full manifest session-receipt hashes equal c931ca11b5cf49052b76188e5ff5bf4f99a9637bc6dab3372da91e250ccfb811. Full campaign unified session 45127 exited 0. Root stopped the resident service with the shared receipt-bound stopper at 03:14:34 UTC after both score jobs finished. No automatic restart or replay occurred. The root-stop.log records SIGTERM, forced=false; the wrapper subsequently reaped exit 0. Historical fit wrapper 45471 and server/monitor PIDs are no longer live ownership instructions. Do not restart this closed session.

The actual G2 argv was decoder-only `--no-mmproj`, c65536, np8, b2048, ub512, q8_0 KV and max64 intent output. Model files contain only the decoder GGUF; all query features were already prepared. Actual maximum request requirements were 2,701 and 2,714 tokens in 8,192-token slots. G1 used no mmproj too, but its actual largest request exceeded 8,192 tokens, so its four-slot configuration cannot simply become eight slots. KU-S3 slot output remains the approved max256 setting.

Full run identities:

- N: SAEA-SLURP-KUS4N-CANDIDATES-DEV1000-V3 / attempt-20260910T020504Z-938cd3.
- Twin: SAEA-SLURP-KUS4N-CANDIDATES-TWIN-DEV1000-V3 / attempt-20260910T020504Z-a556a2.
- All actual fits and inherited four-row smokes remain completed as STATUS-016 records. Do not repeat them.

## Formal G2 result and scientific routing

The frozen config `configs/experiment/slurp-kus4n-g2-aligned-analysis-v1.json` acquired only the four pending manifest/score hashes, committed at efab93994d78c317e047e3c325057ea88303b440 before the one analysis read. The shared score_compare_cli read completed with exit 0, zero model/encoder/tokenizer/scorer calls, 10,000 paired speaker-cluster replicates and frozen seed offsets. Its result is DATA/analysis/SAEA-SLURP-KU-S4N-G2-ALIGNED-READOUT-V1/contrasts.json, SHA256 d296f01467ae388d05b3c932b961e603d8edd94007c92de523b3019b40533e16. The launch PID 354 and unified session 93636 are completed, not running.

Root decision `KU-S4N-G2-ALIGNED-DECISION-V1` is **HOLD_NONINFERIORITY_FAILED**, in `docs/checks/speech-aware-evidence-acquisition/2026-09-10-ku-s4n-g2-readout/decision.json`; the adjacent README carries primary gates, natural/equal-scenario weights, all primary NEW500 strata and source bindings. The complete shared artifact retains both score views, three populations, all contrasts and sensitivities.

On historically exposed NEW500, N minus historical comparator intent is -2.200 pp, CI90 [-5.077, +0.820], against operational NI margin 1.263 pp. Action is -2.600 pp, CI90 [-5.455, +0.232], and pooled micro SLU-F1 is -11.744 pp, CI90 [-15.181, -8.158]. Those gates fail. Scenario improves +1.800 pp and passes NI. N minus twin intent is +32.000 pp, CI90 [28.106, 36.031], but that cannot replace baseline effectiveness and protection gates. No effectiveness or equivalence admission follows. NEW500 remains historically exposed, never a fresh holdout.

G3 exemplar encoding and G4 a/b/c remain held. Do not encode the 7,049 missing exemplar recordings or fly a/b/c automatically. Preserve G1 KU-S3 ADMITTED_COMPONENT (+6.637 pp mean sample SLU-F1 against its matched control on NEW500) and its closed same-process trio. G2 failure does not revoke that different component's admission. Independent E21 model-free preparation continues; G5 and G6 are incomplete, so the overall goal remains active.

A descriptive sealed-output audit found 273 predicted entities in the historical comparator's NEW500 outputs versus 115 for N and 121 for twin. This is not a causal diagnosis. N and twin share the control turn, while the historical comparator lacks it. Root requested a bounded read-only lookup of already sealed no-supply phase-direct-only runs with matching roster, prompt, packets, geometry and output cap. Do not generate a new matched control unless a named mismatch can change a decision and the necessary registration/authorization is complete. No adaptive repeat is authorized.

## Efficiency receipt

The accepted resource audit is DATA/analysis/SAEA-SLURP-KU-S4N-G2-CAMPAIGN-V3/timing-audit-v2.json; canonical timing-receipt.json pins it. Preserve but do not use its V1 predecessor, which incorrectly marked available costs unavailable and called all post-generation time scoring tail. Root re-read the exact manifests and monitor samples.

The whole monitored session time-weighted GPU utilization was 22.203%, with 23.715% slot occupancy. N live-wave-to-seal averaged 72.394% GPU and 78.766% slot occupancy; twin attach-to-seal averaged 63.603% GPU and includes setup. No interval is claimed to be pure kernel-active time. N seal to twin attach took 186.153 seconds, missing the one-minute target. Prepare durable requests before service load and reuse their verified bindings in later workers; do not change closed-run artifacts or add contacts to keep the GPU busy. `monitor.requests_total` is not cumulative generation authority; sealed `cost.calls_used` is authoritative. STATUS-016's interpretation of that counter is superseded.

## Shared E21 engineering integrated

Canonical master includes:

- Verified E21 one-call construction subsets and the exact-four real fitter/OJW/controller synthetic integration (source 75f536c7, canonical 6d370a8f). Root reviewed the entire chain and independently ran 11 passing tests. The four-row prototype remains model-free and held; its historical GPU-mmproj fragment cannot authorize live use. Live Reviewer/Planner/relisten propagation remains a G6 gap.
- Exact-window inventory through `core.preparation_windows`, source fe193c03 plus 02a98def, canonical 52cbfbaf and 56bab0aa. It binds actual slice and parent bytes, request iteration, payload duration/rate and pinned encoder identity; deduplicates exact bytes across named batches; persists through shared prepare_artifact. Root requested and verified a real materializer/repair-hook consumer test including transformed WAV duration. Root inventory tests: 14 passed; helper broader regression suite: 58 passed.
- Public strict legacy-cache inspection through `core.model.speech_features`, source 681dc05c plus 3affdbbd, canonical 6bdc2651 and 2f9f18a6. It reuses the existing chunk parser, exposes audio/chunk hashes and shape metadata, and rejects noncanonical ordinal names or paths outside the declared cache. Historical promotion behavior stays intact. Root affected/preservation tests: 11 passed; helper full packet suite before the narrow follow-up: 67 passed.

Neither inventory nor inspection creates neural features, performs model contact or proves runtime cache hits. They still need shared FlightRuntime preparation/consumption wiring and complete receipt validation.

## Runtime cache guard and next work

The opt-in `LLAMA_MTMD_FEAT_CACHE_REQUIRE_HIT` patch is committed in isolated `/home/chao/llama-worktrees/featcache-require-hit` at cddb000cb45ab44d33c84483cf5e5962cbbaa5bf. Its isolated build at build-qualify linked successfully; binary SHA256 33c80bb2eceb29b8e81739cf0d799fe8d5fb754f73f047aba3c34838f06c66c1. The original runtime at `/home/chao/llama.cpp-featcache` and original binary d0b42ace8d8e02dc772a0e4a1e1667068b3ad799b1ca4c98c741cf89d58404f2 are untouched. Source tests and compilation are not live hit/miss qualification. Build provenance, including exact UI workaround inputs and commands, is committed under docs/readiness/2026-09-09-featcache-require-hit-*. The actual cache filename convention already matches Python: decimal FNV plus `_o<ordinal>.feat`; no format migration is required.

Next priorities:

1. Finish the existing-run control-turn audit and root interpretation without new model contacts. Keep the formal failed G2 gate unchanged unless a separately justified protocol amendment is approved.
2. Wire the shared window inventory and strict cache inspection into ahead-of-run preparation and per-request consumption, reusing the existing four-fragment FlightRuntime entry and generic immutable preparation receipts. Deduplicate before encoding; bind exact audio, cache chunks, build, decoder/mmproj weights and preprocess/stop receipts. No feature claim may be inferred from PCM slicing.
3. Prepare a bounded E21 cache/bridge qualification using the registered construction roster and fresh current-build exact-window cache. Keep mmproj outside GPU memory. CPU-only preprocessing is compatible with the latest owner instruction; any separate GPU encoder window still needs resolution of the pending placement clarification. Do not run the old cross-build cache or old GPU-mmproj E21 configuration.
4. Prove strict cache hit/miss and malformed/decode-failure refusal before encoding, register the new runtime identity, then bind actual full-roster request fit and a whole-comparison service geometry. No formal E21 generation is currently admitted by the held V2 configs.
5. Continue accepted DR as two generation groups with four correlated deterministic deliveries, then LOOP and its twin with registered 600 relistens each and family GPU cap 1.0 hour. Complete shared live system baselines afterward using qualified components; component replay is not full-system performance.

All authored documents and model-facing content are English. All research execution is in WSL Ubuntu-24.04 with explicit checkout PYTHONPATH and no editable-package reinstall. Root owns scientific decisions and the only service; lower-cost helpers perform bounded coding/reading. No paid experimental API, new carrier, Stage-3 scope, publication or automatic replay is authorized.

## Completed existing-control lookup

The metadata-only lookup is now complete; root verified the closest four-row manifest and enumerated canonical direct-phase policies. No full DEV-1000 no-supply control with the added phase turn was found. The only matching engineering smoke has four rows, despite its manifest split name saying DEV-1000. See the G2 readout directory's existing-control-audit.md. This does not change the failed NI gate or authorize new contacts. Next work is shared E21 feature preparation and runtime qualification, with any further G2 causal-control proposal requiring a concrete protocol decision.
