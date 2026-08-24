# DEV-100 C3 prompt-fit bound (`speech-query-blend`, `speech-query-prefix-v2`)

## Decision

**The C3 evidence-conditioned prompt does NOT fit one 4,096-token slot of the
resident `-np 16` service.** The worst-case evidence-decode envelope is
**7,773 prompt tokens** against 4,096 available, a margin of **−3,741** after
the 64-token completion reserve. The direct-decode envelope fits comfortably
(1,819 tokens, **+2,213** margin).

This is a blocking prep result for the DEV-100 campaign, not a passing
certificate. **Round 0 cannot fly on ANY `-np 16` service at this `-c 65536`, as
composed** — the constraint is the 4,096-token slot the composed model
fragment yields, not the particular process that measured it. The campaign fragment, the promoted packets, and the runtime view
are unaffected and remain correct; what must change is either the serving
slot size or the C3 prompt itself. The two remedies are quantified below.

No model contact was made. Tool contacts were exactly 1 `GET /props`,
2 `POST /apply-template`, and 4 `POST /tokenize` against the resident
decoder-only session on port 8080 — zero completion requests, zero decoder
evaluations, zero generated tokens. Pre-registered as
`SAEA-SN-MF-DEV100-C3-PROMPT-FIT` before it ran.

## Session status (added when this receipt was landed)

The service these measurements were taken against, `SAEA-SN-Q4KM-NP16-HOT-PREFIX-ZCOPY-20260823T111700Z` (PID 607, session receipt
`33639d3d…9698`), **terminated after this measurement completed** and is gone
(no `llama-server` process, 0 MiB VRAM in use, host RAM released). The
measurement itself was made against that service while it was alive and
healthy: `prompt-fit.json` was written at 2026-08-24T03:50:39Z, and the seven
tokenizer-only tool contacts it records all succeeded.

The service's `server.log` last wrote at 2026-08-23T18:19:16Z and ends cleanly
on `srv update_slots: all slots are idle`, with zero error, OOM, CUDA-error, or
context-overflow lines in all 1,117,739 bytes. **A frozen log is not death
evidence for this build**: it emits no request-path lines for tokenizer-only
endpoints, so the `/props`, `/apply-template`, and `/tokenize` traffic that
produced this receipt 9.5 hours later left no trace in it. The true termination
window is therefore 2026-08-24 03:50:39Z – 04:32Z, cause undetermined and
unlogged.

**None of the numbers below depend on that session.** Token counts are
properties of the pinned decoder and the chat template (`45777d2e…da8c`), both
recorded in `prompt-fit.json`, not of the process instance — they reproduce on
any session started from the same runtime receipt. What is stale is only the
liveness binding: a future flight must cite its own session, not PID 607.

## Bound identities

- Audit artifact SHA-256:
  `3468461c22a04baae46365f30a192c2b65332a223d0992fda8eeeb5bc3db1e30`
- Composed config hash:
  `668a0f1c6adfc11228535dd6bcedf56284c446551077a1e137576533e8b638dd`
  (model `q4km-mmproj-free-speech-native-np16-zcopy-speech-query-prefix-max64`
  / dataset `slurp-speech-native-dev100` / baseline
  `slurp-dev100-kb-alpha-blend` / experiment
  `slurp-dev100-kb-alpha-blend-campaign-v1`)
- Knowledge snapshot SHA-256:
  `e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57`
- Packet promotion receipt SHA-256:
  `8d2dc4dc9056ed604b22cbb66cd46724d3ee0246b6aca5665e6bfaf67cf0503d`
- Chat template SHA-256:
  `45777d2e798aae1d1ce6844e69edcb23fc0c710009554711c78efab9044da2c8`
- Resident service: PID 607, port 8080, `--no-mmproj`,
  `-c 65536 -np 16` → 4,096 context tokens per slot. This is not an
  inference from the arithmetic: the service's own startup log printed
  `slot load_model: id N | task -1 | new slot, n_ctx = 4096` for each of
  the 16 slots.

## Why this is a new bound and not the existing audit

`saea-driver speech-native-prompt-audit` enumerates envelopes by driving
`run_speech_native_match_tasks` over `KeyCardV1` + `DecisionGraphV1`, and
`_enumerate_m11_prompt_envelopes` hard-requires `top_k` in
`[2, min(3, key count)]`. The C3 chain uses none of those objects: its prompt
shapes come from `rails.runner._agent_messages`, its evidence comes from the
`saea-fuse-supplyfilter-v1` fusion decision, and its top-k is 5. Forcing the
M11 enumerator would have certified a prompt the campaign will never send.

This bound instead renders the real C3 shapes through the real functions —
`rails.runner._agent_messages` for message construction,
`core.model.transport._ordered_speech_feature_content` for the
`speech-query-prefix-v2` wire layout, and
`core.model.transport._speech_history_texts` for the ORG/CONTROL suffix — and
tokenizes the resulting wire request through the same
`/apply-template` + `/tokenize` boundary the M11 receipts use. Generator:
`scripts/dev100_c3_prompt_fit.py`.

## Envelopes

| envelope | text tokens | + speech | + special | upper bound | margin |
|---|---|---|---|---|---|
| `direct-decode` | 1,700 | 117 | 2 | **1,819** | **+2,213** |
| `evidence-decode-worst` | 7,654 | 117 | 2 | **7,773** | **−3,741** |

Speech-feature allowance is the maximum over the five longest DEV-100
packets (117 tokens, `slurp/devel/004545/audio-1497450582` at 8.13 s).

## What makes the evidence envelope worst case

Three terms, all upper-bounded on purpose:

1. **The task contract, counted twice.** `_agent_messages` appends the full
   TRAIN ontology roster (5,424 characters) to the system message, and
   `rails.kb_policy`'s `_advance_after_recall` builds the evidence contact's
   control instruction as `f"{context.task_contract}\n Answer using..."` — so
   the same roster is rendered again as the `[agent control evidence-decode]`
   suffix.
2. **Fused values.** At the round-0 knobs (`fusion_m` 5, `fusion_c` 2,
   `fusion_top_l` 3) the fuser can emit up to six values; the six LONGEST
   value contents in the snapshot were used.
3. **Visible key facets.** Up to five, and the five LONGEST facet
   representations were used.

Selecting the longest of each is exactly the maximum over every reachable
fusion decision, so 7,773 is the true ceiling, not a sample.

## How much of that is the duplication, and how much is the evidence

Measured decomposition (the two envelopes differ only by the evidence and
control text): 5,954 tokens for 16,719 characters, i.e. **2.807 characters
per token** on this tokenizer and template.

The snapshot's own text-length distribution (model-free, no contacts;
11,863 facets and 11,514 values):

| | min | p50 | p90 | p99 | max |
|---|---|---|---|---|---|
| `facet.representation` | 1 | 33 | 60 | 228 | 525 |
| `value.content` | 310 | 621 | 855 | 1,171 | 1,581 |

Values dominate: mean 647.7 characters each, and the fuser emits up to six.
Applying the measured characters-per-token ratio to a 5-facet + 6-value
selection (these are ESTIMATES, not measurements — only the two rows in the
table above were tokenized):

| evidence selection | evidence chars | est. total upper bound | est. margin |
|---|---|---|---|
| median-length | 3,891 | ≈ 5,162 | ≈ −1,130 |
| p90-length | 5,430 | ≈ 5,710 | ≈ −1,678 |
| worst (measured) | 11,225 | 7,773 | −3,741 |

**The typical case overflows too.** Even a median fusion decision is
estimated at ~5,162 tokens against 4,096 — a ~26% overshoot, far outside any
plausible estimation error. This is not a tail risk that could be waved
through.

## Two independent remedies, quantified

1. **Serve the campaign at `-np 8`.** 65,536 / 8 = 8,192 tokens per slot.
   The measured worst case of 7,773 + the 64-token completion reserve = 7,837
   fits with **+355** margin. `-np 8` is the largest slot count that admits
   the true worst case; `-np 16` cannot, at any evidence selection. This
   requires a different model fragment and a different resident server — the
   campaign cannot attach to the current PID 607 service.
2. **Stop repeating the task contract in the control instruction.** The
   duplicated roster is 5,494 characters ≈ **1,957 tokens**. Removing it
   brings the estimated median envelope to ≈ 3,230 tokens (margin ≈ +802) and
   the p90 envelope to ≈ 3,778 (margin ≈ +254), but the p99 envelope to
   ≈ 4,753 — still over. So this remedy alone is not sufficient, and it is a
   `rails/kb_policy.py` change that belongs to whoever owns that policy, not
   to this prep mission.

Remedy 1 alone is sufficient for the true worst case. Remedy 2 alone is not.
Both together leave the worst case at ≈ 5,816 tokens in an 8,192-token slot.

## Percept admission runs facet-side — the value vectors stay sealed

Verified against the source while landing this receipt, because the campaign's
knowledge vectors include a value-vector family that the owner's Q-K-V ruling
(section 1.3) seals: **V is consumed, never embedded as key material.**

`rails/kb_policy.py` already satisfies that ruling with no change required.
`multidim_recall` computes cosines strictly between `query_vectors[dimension]`
and `facet_vectors(facet_id)[dimension]` — facet vectors only. The fuser's
percept-admission test (`_fuse_supply_filter`'s `admitted()`) reads those same
facet cosines out of `recall_scores`, and a value is admitted only when its
`associated_facet_ids` intersect the admitted facet set. **No value vector is
read anywhere in the policy.** The embeddings receipt
(`docs/receipts/knowledge/slurp-kb-size-full-embeddings.json`) states the same
constraint in its own `consumption_caution` field.

So the campaign can run facet-side exactly as designed, and the value vectors
remain available for evidence-side work (deduplication, supply-side reranking,
diagnostics) only. No policy change was needed and none was made.

## Scope

This receipt bounds token geometry only. It authorizes no campaign round, no
inference, and no semantic reading. It does not evaluate whether the C3 chain
is effective, and it makes no claim about accuracy, contacts, or cost.
