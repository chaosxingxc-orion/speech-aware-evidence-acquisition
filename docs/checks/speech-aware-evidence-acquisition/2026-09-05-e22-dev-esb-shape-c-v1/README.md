# Earnings-22 DEV ESB shape C, v1 — receipts

One registered arm on the **sealed prompt-A/B roster**, paired against both arms already flown.
Preregistration: `docs/readiness/2026-09-05-e22-dev-esb-shape-c-v1-preregistration.md`.

| run id | arm | request shape |
|---|---|---|
| `SAEA-E22-DEV-ESB-PROMPT-A-V1` (sealed 2026-09-05) | A, control | `[system: instruction][user: audio]` |
| `SAEA-E22-DEV-ESB-PROMPT-B-V1` (sealed 2026-09-05) | B | `[system: instruction][user: audio]` |
| `SAEA-E22-DEV-ESB-SHAPE-C-V1` | C, this flight | `[user: audio, instruction]` — **no system message** |
| `SAEA-E22-DEV-ESB-SHAPE-C-SMOKE-V1` | C, 4 rows | go/no-go |
| `SAEA-E22-DEV-ESB-SHAPE-C-PROMPT-FIT-V1` | A, B and C | the rendered-template proof, zero generated tokens |

Arms B and C send the **same instruction string**, byte for byte
(`Transcribe the English audio into text.`, sha256 `8533f771…`). The only thing that differs between
them is where that string sits in the request.

## What is here

| path | what it pins |
|---|---|
| `prompt-fit/prompt-fit.json` | the arithmetic window fit for arm C on the 6,038-row roster, at zero contacts of every kind: worst request 2,102 tokens against a 5,120-token slot, ×2.44 |
| `prompt-fit/prompt-fit-smoke4.json` | the same, for the 4-row smoke roster |
| `prompt-fit/prompt-fit-render.json` | **the rendered-template proof**: the full rendered prompt for all three arms through the pinned GGUF chat template, with the wire messages captured from the real `LlamaServerTransport`. Arm C renders with no system block at all; arms A and B still render theirs. Zero generated tokens |
| `wire-check/` | the whole request path for both arm-C cells through a fake gate and a fake transport — zero model contacts, zero servers, zero sockets |
| `smoke/` | the 4-row go/no-go and its flight receipt |
| `flight/` | the flight receipt |
| `verdict/` | `result-summary.json` (all three arms' sealed numbers, both paired contrasts, the error-shape decomposition, the length ratio by duration bucket and the decision) and `per-arm-tables.md` |

The roster, the segment table, the derived reference layer and the prompt source are **not**
duplicated here: they are the sealed A/B artifacts, under
`docs/checks/speech-aware-evidence-acquisition/2026-09-05-e22-dev-esb-prompt-ab-v1/`, reused by name
and by hash.

## Boundary

**No confirmatory call is named, loaded, decoded, scored or read.** The ten calls here are this
study's registered `dev` subset10 (`docs/receipts/splits.json`, identity `89b178d6…`), the split it
may optimize on, and they are the same ten the sealed A/B already read. The six calibration-exposed
ESB **test** calls of 2026-09-04 are not read again. The 109 calls that remain confirmatory, the six
ESB validation calls among them, are untouched.

References never enter the request path: the roster receipt the flight entry point reads carries
identifiers, media paths, measured media identity and segment spans only.
