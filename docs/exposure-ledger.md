# Exposure ledger

Every model or tool touch (including a single-sample smoke) gets a row **before results are read**.
Exposure claims elsewhere must carry four fields: scope, date, counts, inherited exposure.

Field semantics (consolidated contract §6/§7; umbrella 续92/续93):

- `execution profile` — one of `model-free-check` / `baseline-reproduction` /
  `bounded-discovery-probe`; paper-scale profiles never appear in this ledger.
- `split role` — `discovery` or `dev`. `confirmatory` rows require Stage-3 paper authority
  (`OWNER_GO_AND_PAPER_EXECUTION_CONTRACT`) or a dated owner allowance and do not occur in Stage-2.
- `split identity hash` — SHA-256 over the exact sample-identity list this touch may read.
- `consumed` — `yes` only when confirmatory results were read; **irreversible once `yes`**;
  model-free and discovery/dev rows write `no`.
- `inherited exposure` — scoped statement of prior exposure carried into this touch;
  monotonically non-decreasing across rows.
- `calls` / `speech audio seconds` / `gpu hours` — the registered budget record for this
  run; every cell must be a **finite non-negative number** (the gate refuses NaN or
  negative cells outright — they would corrupt the arithmetic). These columns carry no
  numeric ceiling of their own (the first-slice caps that used to sum them as slice
  totals — consolidated contract §6 — were retired by the 2026-08-06 owner amendment,
  `SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS`): `contracts.FrozenCoreGate` no longer sums
  these columns across rows. What it still enforces, per row, is the cross-check that a
  plan may only claim what its OWN matched row registers: `registered ≥ planned` for each
  of the three columns, against the plan's own declared `planned_model_calls` /
  `planned_speech_audio_seconds` / `planned_gpu_hours`.

Inherited exposure baseline: program-level prior exposure (W1 probe campaigns on other carriers; no
Earnings21/Earnings22/ConEC model exposure inherited as of 2026-08-03). The carriers' only
processing so far is model-free acquisition/verification (D0).

| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-08-04 | SAEA-E0-CLOSURE-2026-08-04 | model-free-check | E0 D1–D4 closure + runtime receipt + gate dry-run: identity/byte enumeration of the three core carriers; ten-sample e22 subset10 provenance trace; GGUF + llama.cpp build/bin hashing; no audio decoded, no annotation content parsed into artifacts, no model loaded | none beyond local tooling (filesystem hashing; contract negative controls; local `git` metadata; `llama-server --version` build-hash query — no model file passed) | earnings21-original + earnings22-original + conec, identity layers; e22 subset10 (dev) | dev | 99a896359a504f463a1657281aa71f4a28a51161c804422d8e2f192b0486ad3e | no | 0 | 0 | 0 | W1 probe campaigns on other carriers; zero model exposure on the three core carriers | docs/receipts/e0-closure.json + docs/receipts/artifacts/ + docs/receipts/runtime.json | model-free; split identity hash = SHA-256 over the 213 carrier-prefixed sample IDs enumerated (44 e21 + 125 e22 + 44 conec); scope amended same-day after round-1/round-2 adversarial review to name the runtime receipt/tooling and add the gpu-hours budget column (git history preserves prior text) |
| 2026-08-08 | SAEA-E-001-r0-smoke | bounded-discovery-probe | R0 smoke per docs/runbooks/2026-08-05-r0-smoke.md: bare-core long-form ASR wiring + measurement-integrity smoke on the frozen e22 dev subset10 (10 samples + 2 retry headroom); first model touch of the study | Qwen3-Omni-30B-A3B-Instruct GGUF (lock key qwen3-omni-30b-a3b-instruct-gguf) via receipt-pinned llama.cpp llama-server build fdbd6abee20e408de21e90ca77a24cd50a6ea073, spawned by core.session per session receipt | earnings22-original, dev subset10 | dev | 89b178d6b1ef46d9ca820ae54349e3d2099c60cde6d6b753ef9f66137c310028 | no | 18 | 63600 | 6.0 | E0 closure row above (model-free identity/byte layers on the three core carriers); W1 probe campaigns on other carriers; zero prior model exposure on e22 | $SPEECHRL_DATA_DIR/runs/SAEA-E-001-r0-smoke/<attempt_id>/ (plan, session receipt, run manifest, trace, scores, ledger row) + local MLflow (ext4 ~/mlruns) | authority: 2026-08-08 owner GO record (umbrella wiki/experiments/.../2026-08-08-owner-go-baseline-reproduction.md); planned_gpu_hours 6.0 supersedes the runbook's 2.0 example (operator planning decision, headroom for ~11.1h audio through the 30B core); pre-registration note: before this row existed, smoke --dry-run validation attempts (no model, dry transport) briefly used this run-id's namespace — their runs/ and attempts/ debris was removed and all later validation moved to the SAEA-E-001-r0-smoke-dryrun namespace (final validation attempt attempt-20260808T042700Z-b1fac1 FINALIZED, dry_run=true); consumed stays no until results are read post-run; **2026-08-08 extension (runbook discipline, before any result read)**: three aborted wiring attempts each burned 1 metered call + the first sample's audio seconds before failing (503-during-load → readiness-wait fix; bare HTTP 400 → transport-diagnostics fix; HTTP 400 = 56,032 tokens > n_ctx 4096 → server_args in the model config: -c 65536, -fa, -ngl 999, experts-on-CPU override; request timeout 300→3600s) — planned calls 12→18 and audio-seconds 49,446→63,600 to keep the 10-sample run inside the plan-level cross-attempt meter; git history preserves the prior cells |

| 2026-08-08 | SAEA-E-002-r4-nocontext | bounded-discovery-probe | R4/P2b context-dose probe, arm 1/3 (bare-core, no evidence): long-form ASR on the frozen e21 discovery split (44 samples + 2 retry headroom); first model exposure on earnings21 | Qwen3-Omni-30B-A3B-Instruct GGUF via receipt-pinned llama.cpp build fdbd6abee…, spawned per session receipt | earnings21-original, discovery split (44) | discovery | fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e | no | 46 | 152830 | 20.0 | E0 closure + SAEA-E-001 (e22 dev smoke); zero prior model exposure on e21 before this row | $SPEECHRL_DATA_DIR/runs/SAEA-E-002-r4-nocontext/<attempt_id>/ + local MLflow | authority: 2026-08-08 owner GO; experiment fragment configs/experiment/r4-context-dose.json; arms run sequentially after SAEA-E-001 finalizes; dry-run validation only in the -dryrun namespaces |
| 2026-08-08 | SAEA-E-002-r4-matched | bounded-discovery-probe | R4/P2b arm 2/3 (fixed-legal-context: each sample's own ConEC contexts-layer materials in SUPPLY) — same split, same instruction as arm 3 | same as arm 1 | earnings21-original, discovery split (44) | discovery | fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e | no | 46 | 152830 | 20.0 | as arm 1, plus arm 1 once it runs (rows in this block are one pre-registration batch) | $SPEECHRL_DATA_DIR/runs/SAEA-E-002-r4-matched/<attempt_id>/ + local MLflow | evidence = D1-frozen conec e21_contexts layer only; oracle/gold evidence hard-raises on the runtime path |
| 2026-08-08 | SAEA-E-002-r4-mismatched | bounded-discovery-probe | R4/P2b arm 3/3 (mismatched-evidence: deterministic rotation derangement of the same contexts across the 44 ids; negative control) — instruction text equalized with arm 2 on 2026-08-08 so the arms differ only in evidence content | same as arm 1 | earnings21-original, discovery split (44) | discovery | fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e | no | 46 | 152830 | 20.0 | as arm 2 | $SPEECHRL_DATA_DIR/runs/SAEA-E-002-r4-mismatched/<attempt_id>/ + local MLflow | success criterion (pre-registered): WER(matched) < WER(no-context) and WER(matched) < WER(mismatched); per-entity-class WER deferred (no owner-pinned wer_tags adapter) |

(a model touch additionally requires the runtime receipt and a validated `ExecutionPlan`
whose `run/experiment id` is pre-registered above, per the consolidated execution contract)
