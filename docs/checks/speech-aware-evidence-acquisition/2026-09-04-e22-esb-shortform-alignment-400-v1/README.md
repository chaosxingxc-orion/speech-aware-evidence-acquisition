# SAEA-E22-ESB-SHORTFORM-ALIGNMENT — receipts

The Earnings-22 short-form cell against the **only same-model published number** this study can
reach on any carrier. Verdict:
`docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-verdict.md`. Preregistration, with the
full phase log: `docs/readiness/2026-09-04-e22-esb-shortform-alignment-v1-preregistration.md`.

**NOT ALIGNED — 15.937 % corpus WER under the Whisper `EnglishTextNormalizer` over all 2,735
published ESB test utterances, against Qwen3-Omni-30B-A3B-Instruct's own published 9.79** (+6.15)
and its cross-read 12.3 (+3.64). Band test (<= 12.79), strict `whisper-large-v3` floor (<= 11.59)
and loose `whisper-base.en` floor (<= 15.09) all fail; only `whisper-tiny.en`'s 19.12 is cleared.

The gap has a shape: insertions are 59.2 % of all errors, the hypothesis runs 1.0749x the reference
in length, and an **oracle** cut to the reference's own word count -- a diagnostic bound, never an
achievable result -- moves the figure 5.48 points to 10.456, inside the band. Output discipline,
not acoustic recognition.

A note on this directory's name: it carries `-400-` from the brief that commissioned the cell. The
population is **2,735** utterances, not 400. The path is kept as commissioned so every receipt,
config fragment and ledger row points at one place; the count in the name is wrong and is recorded
as wrong here.

| directory | what it holds |
|---|---|
| `segment-table/` | the pinned identity of `sanchit-gandhi/earnings22_split` split `test` at revision `f9fb35f4`: all four parquet shards by size and git-LFS oid (each re-hashed locally and each matching), the pyarrow column-projection method that never materialized the `audio` column, the extracted 2,735-row table's own SHA-256, the per-call segment counts, and the **unresolved** 2,735-vs-2,741 row-count gap against the leaderboard's published N. A derived-split reference pinned by hash, never a new umbrella lock asset. |
| `roster/` | the 2,735 cut utterances: id, parent call, parent bytes as D1 recorded them, derived media path, measured SHA-256, measured duration, the published segment span, and the three end boundaries clamped to the decoded parent. Identifiers and media identity only -- no reference text, because the flight entry point reads this file. |
| `reference-layer/` | the SHA-256, row count and word count of the derived per-utterance reference layer. The bytes themselves live under `$SPEECHRL_DATA_DIR` and never enter Git; `reproduction.esb_reference.load_esb_references` re-hashes them against this receipt before a scorer reads a word. This is what replaces the D1 reference-identity gate, which fails closed for any id outside a carrier's `nlp_references` manifest -- and an ESB utterance is exactly that. |
| `wire-check/` | both cells driven end to end against `WireCheckGate` and `WireCheckTransport` on a clean committed tree: 4 of 4 and **2,735 of 2,735** contacts through the real compose, adapter, payload binding, allowlist, attempt accounting, manifest builder, bundle verifier and both new scorers, with `core.scoring_batch` reporting `verified: true`. Zero model contacts, zero servers, zero sockets. The WER figures inside are computed over the transport's canned response and measure nothing. |
| `smoke/` | the live 4-row rehearsal, `SAEA-E22-ESB-SHORTFORM-ALIGNMENT-SMOKE-V1`, on the longest / shortest / median / p90 utterance. Proves the two ESB scorers run on a live sealed manifest, proves `-c 32768 -np 8` serves with the resident bf16 mmproj, and measures the text envelope at **exactly 49 tokens** on all four requests -- so the worst prompt is 530 against a 4,096-token slot. |
| `verdict/` | `result-summary.json` (every number the preregistration made mandatory, plus the preregistered decision applied) and `per-call-table.md` (all six calls, the duration deciles, and the three clamped utterances). |

Sealed run artifacts (outputs, trace, manifest, scores, session receipts, server log) are under
`$SPEECHRL_DATA_DIR/runs/SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1/<attempt_id>/` and never enter Git, as
do the 2,735 derived utterance WAVs under
`$SPEECHRL_DATA_DIR/derived/e22-esb-utterances/v1/` (623,947,810 bytes) and the derived reference
layer under `$SPEECHRL_DATA_DIR/derived/e22-esb-segment-table/`.
