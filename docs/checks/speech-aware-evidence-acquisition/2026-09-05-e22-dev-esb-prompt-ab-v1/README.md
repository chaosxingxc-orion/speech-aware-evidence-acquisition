# Earnings-22 DEV ESB prompt A/B, v1 — receipts

One registered experiment, **two paired arms**, on this study's own Earnings-22 **dev** subset10 cut
at the ESB `train`-split boundaries. Preregistration:
`docs/readiness/2026-09-05-e22-dev-esb-prompt-ab-v1-preregistration.md`.

| run id | arm | instruction |
|---|---|---|
| `SAEA-E22-DEV-ESB-PROMPT-A-V1` | A, control | the one the sealed ESB **test** flight sent, byte-identical |
| `SAEA-E22-DEV-ESB-PROMPT-B-V1` | B, candidate | `Transcribe the English audio into text.` — the Qwen3-Omni authors' own English ASR prompt |
| `SAEA-E22-DEV-ESB-PROMPT-AB-SMOKE-V1` | both, 4 rows | go/no-go |

Exactly one thing differs between the arms: the `task_instruction` string.

## What is here

| path | what it pins |
|---|---|
| `segment-table/segment-table-receipt.json` | `sanchit-gandhi/earnings22_split` split **`train`** at revision `f9fb35f4…`, filtered to the ten dev calls **inside the batch loop**, 6,038 rows, extracted table `51257011…`. The 55 train shards (22.0 GB) are pinned by their published git-LFS oids and were **not** downloaded. |
| `roster/flight-roster-receipt.json` | the 6,038 locally cut 16 kHz mono WAVs, measured identity and segment spans only, `ids_sha256` `dfa2ec01…`, `items_sha256` `37e45e51…`, one clamped utterance (`4481952-631`) |
| `reference-layer/reference-layer-receipt.json` | the derived reference layer (6,038 rows, 104,808 whitespace words, `8da3a65d…`). The bytes live under the controlled data root and never enter Git. |
| `prompt-fit/prompt-fit.json` | the window fit, derived at **zero contacts of every kind** before registration: worst request 2,102 tokens against a 5,120-token slot, ×2.44; the sealed flight's 4,096-token slot would **not** fit |
| `prompt-fit/prompt-fit-smoke4.json` | the same, for the 4-row smoke roster |
| `prompt-source/qwen3-omni-asr-prompt-source.json` | where arm B's instruction comes from: the official model card and the official cookbook, by URL, fetch date and SHA-256, with the lines quoted |
| `wire-check/` | the whole request path through a fake gate and a fake transport, all four cells — zero model contacts, zero servers, zero sockets |
| `smoke/` | the 4-row, both-arm go/no-go, and both smoke flight receipts |
| `flight/` | the two flight receipts, one per arm |
| `verdict/` | `result-summary.json` (both arms' sealed numbers, the paired contrast, the error-shape decomposition and the decision) and `per-arm-tables.md` |

## Result

Arm A **17.565 %** corpus WER (Whisper normalizer) against arm B **18.394 %** over all 6,038
utterances. The paired per-utterance delta is **−0.02741** with CI90 **[−0.0449, −0.0133]** and
the corpus-level delta **−0.830** points with CI90 **[−1.653, −0.172]** — both entirely below
zero, so **arm B is significantly worse** and the prompt is not the explanation for the
2026-09-04 ESB test flight's gap. Verdict:
`docs/readiness/2026-09-05-e22-dev-esb-prompt-ab-v1-verdict.md`.

## Boundary

**No confirmatory call is named, loaded, decoded, scored or read.** The ten calls here are this
study's registered `dev` subset10 (`docs/receipts/splits.json`, identity `89b178d6…`), the split it
may optimize on. The six calibration-exposed ESB **test** calls of the 2026-09-04 flight are a
separate population, with a separate roster, a separate reference layer and a separate derived media
root; they are not read again. The 109 calls that remain confirmatory, the six ESB validation calls
among them, are untouched.

The ESB `train` split carries 113 source calls and 103 of them are confirmatory for this study, so
the extractor drops every non-dev row **before** it can reach a list, a file, a log line or a
receipt. No confirmatory sentence, boundary or per-call count is written down, printed or counted
anywhere in this directory.

References never enter the request path: the roster receipt the flight entry point reads carries
identifiers, media paths, measured media identity and segment spans only.
