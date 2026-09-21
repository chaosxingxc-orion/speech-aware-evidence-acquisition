# Cell B6 preparation plan on SLURP DEV-2000-ADDED, v1

Owner decisions 34, 35, 76a, 78 and 79 (`docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`,
`docs/readiness/2026-09-19-slurp-dev-2000-roster-v1.md`, git commit `51c7ec4d`). This document
states what cell B6 needs before it can fly; it does NOT register cell B6's arms. Both preparations
below are registration-only packages drafted in worktree `fable-dev2000-prep`; neither authorizes a
model, tokenizer, encoder, GPU, network, scoring, or answering contact by itself.

## Order

1. **ENCODE** -- `SAEA-SN-DEV2000-ADDED-PREPROCESS` step 1. CPU-only llama-server sidecar on port
   8081, 1,000 contacts at `max_tokens: 1`, GPU untouched (`-ngl 0`). Package:
   `docs/readiness/2026-09-21-slurp-dev2000-added-preprocess-v1/`.
2. **PROMOTE** -- `SAEA-SN-DEV2000-ADDED-PREPROCESS` step 2, zero contacts, additive-only write to
   the existing served packet root. Same package.
3. **Speech-query encoding** -- `SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1`, CPU-resident
   frozen Omni-Embed-Nemotron-3B retrieval tool, 1,000 tool-level contacts, 0 frozen-core contacts.
   Package: `docs/readiness/2026-09-21-slurp-dev2000-added-speech-query-encoding-v1/`. Runs after
   step 2 closes so it never competes with the sidecar or an answering session for CPU/GPU custody.
4. (Not registered here) a zero-contact alias step that repackages the sealed query vectors into
   `vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl`, following the Fold A/B
   precedent (`docs/readiness/2026-09-14-slurp-native-dual-store-train-source-folds-held-v1.md`).

All three registered steps are CPU-only; the GPU stays free for the resident decoder-only serving
session throughout. Per owner decision 77, each step launches as its own Windows Scheduled Task,
independently stoppable and resumable, rather than as one long-lived process.

## Receipts each step must leave

| Step | Receipt |
| --- | --- |
| ENCODE | Sidecar session + stop receipt (`forced=false`), server-log snapshot before/after the window, exposure-ledger row `SAEA-SN-DEV2000-ADDED-PREPROCESS` marked flown with actual spend |
| PROMOTE | `/home/chao/feat-cache/slurp-q4km-packets-04ccc72a/DEV-2000-ADDED-promotion.json` (fields listed in `docs/readiness/2026-09-21-slurp-dev2000-added-preprocess-v1/plan.json` `promotion_receipt_required_fields`) |
| Speech-query encoding | `prepared/SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1/{index.json,queries.jsonl}`, exposure-ledger row `SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1` marked flown with actual spend |
| Alias (not registered here) | `vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl` plus its own alias receipt (row/segment counts, zero max delta, zero contacts) |

## What cell B6's two arms will bind (not registered by this document)

- **Bare-core direct arm**: the `direct-only` phase program against the promoted packets
  (`DEV-2000-ADDED-promotion.json`), the same harness every other SLURP direct comparator uses.
- **Locked default-plan arm**: `configs/baseline/slurp-native-dual-store-train-fold-a-default-plan-v1.json`,
  re-pointed at the DEV-2000-ADDED promotion receipt and the DEV-2000-ADDED query-vectors alias
  file instead of Fold A's.
- Both arms bind: the promotion receipt (packets), the vectors file
  (`vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl`), the runtime view
  (`configs/dataset/slurp-speech-native-dev2000-added.json`), utterance clustering for paired
  analyses (deviation D2 -- 87 of the 913 added utterances carry two recordings; cluster by
  `utterance_id`, never treat the two as independent), and report BOTH weightings from deviation D3
  (the natural devel mixture and the DEV-1000-style equal-per-scenario weighting).

## Not authorized by this document or by either preparation package

Cell B6's own registration, any model/tokenizer/encoder/GPU/network contact, any scoring read, and
any answer read. Both preparation packages are REGISTERED-BEFORE-CONTACT drafts; each still needs
its exposure-ledger row committed at a clean tree before the corresponding step may fly.
