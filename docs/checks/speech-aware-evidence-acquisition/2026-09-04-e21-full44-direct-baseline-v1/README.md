# SAEA-E21-FULL44-DIRECT-BASELINE — receipts

The Earnings-21 bare-core direct baseline on **all 44 discovery calls**. Verdict:
`docs/readiness/2026-09-04-e21-full44-direct-baseline-v1-verdict.md`. Preregistration (with the
full phase log, including the aborted V1 and the one permitted recovery):
`docs/readiness/2026-09-04-e21-full44-direct-baseline-v1-preregistration.md`.

**ALIGNED — 8.200 % corpus WER under the Whisper `EnglishTextNormalizer` over all 44 calls, against
`openai/whisper-large-v3`'s published 9.71.** Band test (<= 12.71) and strict floor test
(<= medium.en 10.2) both pass; ALIGNED-BETTER (< 6.71) not reached.

| directory | what it holds |
|---|---|
| `window-fit/` | the pre-flight fit certificate, **zero model contact**: the sealed 2026-08-14 arm's own 342 `COST` records give a constant 62-token text envelope, a worst prompt of 1,232 tokens and a worst requirement of 2,258 against a 6,144-token slot (x2.72). Trace sha256 re-verified against its sealed manifest before any number was read off it. |
| `wire-check/` | `core.driver smoke --dry-run` on a clean committed tree: 68 of 68 contacts through the real compose, split verification, plan validation, OBS slicing, sealing, all four manifest scorers and finalize, against a fake transport and a no-op gate. Zero sockets, zero servers. The proof that a four-scorer manifest actually scores. |
| `smoke/` | the live 68-window rehearsal, `SAEA-E21-FULL44-DIRECT-BASELINE-SMOKE-V1`. Proves the VRAM the window-fit receipt could not (23,396 MiB of 24,463 at `-c 49152 -np 8` with the mmproj on the GPU), confirms the derived 1,232-token worst prompt live, and measures the throughput the flight's go/no-go was computed from (16.29 s per window against the sealed arm's 89.15 s: 5.47x). |
| `entity-annotation-defect/` | scope and regression anchor for the `data.references` repair. One entity id, on one call, covering one tagged token, out of 38,377 ids and 55,294 tagged tokens in the release's own annotation layer — and it refused all four scorers on a sealed 44-call run. The anchor holds to the digit: the sealed ten re-score to the audit's published 32.01 % over 8,284 mentions. |
| `scoring/` | the `core.scoring_batch --include-per-sample` **verified** read of the sealed V2 manifest (`verified: true`, one whole-manifest job, never sharded), plus its batch summary and job file. Per-sample `ref_hit_mask` arrays were dropped for size; every count is retained verbatim and the unreduced file's sha256 is recorded inside. |
| `verdict/` | `result-summary.json` (every number the preregistration made mandatory, plus the preregistered decision applied) and `per-call-table.md` (all 44 calls including `4346923`). |

The roster/identity receipt for the population lives beside this directory at
`../2026-09-04-e21-full44-roster/flight-roster-receipt.json`: 44 calls, 141,348.532 s (39.2635 h),
1,593 fixed 90-second windows, split identity `fcc1b0bc...d69e` recomputed against the frozen
`docs/receipts/splits.json`, all three data layers materialized for every call.

Sealed run artifacts (outputs, trace, manifest, scores, session receipts, server log) are under
`$SPEECHRL_DATA_DIR/runs/SAEA-E21-FULL44-DIRECT-BASELINE-V2/attempt-20260904T233816Z-bcd338/` and
never enter Git.
