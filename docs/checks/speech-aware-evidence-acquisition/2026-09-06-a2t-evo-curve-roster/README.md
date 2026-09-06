# EVO-A1 curve roster — `A2T-EVO-CURVE-400-V1`

Model-free, zero contacts, no GPU. Exposure row `SAEA-SN-MF-A2T-EVO-CURVE-ROSTER-V1`. Generator
`scripts/build_a2t_evo_curve_roster.py`; receipt shapes `core/roster.py` (`freeze_roster`) and
`analysis/a2t_evo_rosters.py` (`flight_roster_document`). Outbound connection attempts: **0**.

Authority:
`docs/readiness/2026-09-06-a2t-evo-a1-description-evolution-v1-preregistration.md` section 7 and
open point 4 — the curve roster was the document's second open decision. The coordinator closed it
on 2026-09-06 as **Option A**.

## What it is

A 400-row, tier-stratified (50 per tier) **subset** of the sealed `A2T-ORG1-UNION-4000`, drawn
**once** by `core.roster.freeze_roster` at seed 20260906, `split_role = "discovery"`,
`roster_role = "evaluation"`, strata = tier, no exclusion and no group key (the parent population is
already the sealed draw). It is read once per round by that round's post-decision incumbent and
**decides nothing**: no stage-one gate, no confirmation, no acceptance and no kill rule reads it.

Option A rather than Option B (`A2T-CALIBRATION-400`, of which only 68 rows sit inside the union)
because a strict subset of the final read's population puts the curve and the evaluation delta on
one distribution, so the generalization gap `G = delta_foldB - delta_4000` is not confounded by a
population change.

| fact | value |
|---|---|
| rows | 400 (50 per tier over all eight tiers) |
| distinct `query_idx` blocks | 363 |
| domains | smart_home 281, wearables 82, smart_car 37 |
| audio, one pass | **3,470.346292 s** |
| longest row | **654.635667 s** |
| shortest row | 0.958417 s |
| `split_identity_hash` (FlightRuntime convention) | `b40043be23ed364b5121612b74cfbe52c044e1d83a2139c90229cdd72e92987f` |
| `split_identity_hash` (probe-receipt `key` convention) | `4df3986d29bc98a788d2ab1249e697b4c2c13269e2b3b164b1f959a7db79e49b` |
| roster receipt | `docs/receipts/rosters/a2t-evo-curve-400-v1.json`, sha256 `443e9ac70021c12018f5511d0eca792a70c61270c2b3a79884cf293aad99bbc7` |
| flight-roster receipt | `flight-roster-receipt.json`, sha256 `b22741ac5be7f8bf8be4bd9e46de256ff870aa0f6a6ed7e37d2cc722b9cc3af4` |
| dataset fragment | `configs/dataset/audio2tool-evo-curve-400.json` |

## Two corrections to the preregistration, both measured rather than estimated

**1. One curve pass costs 3,470.346292 s, not the estimated 2,342 s.** Section 7 priced Option A by
scaling the union's 23,418.083 s to 400 rows. The draw inherited **two of the union's four
654-second synthesis defects** (`tier6_correction:003151` and `tier7_multiturn:001033`), which alone
are 1,309.3 s — 38 % of the pass. The rows are **kept**: the sealed baseline outputs this read is
paired against were produced on exactly these rows, and dodging them would make the draw a
selection rather than a subset. The registered ceiling for `SAEA-A2T-EVO-A1-CURVE-400-V1` is
`R_max x` this, **13,882 s**, not the 9,368 s section 10 carried.

**2. The curve cell's serving geometry is the union's, not the folds' looser one.** Under the mmproj
encoder's one-second window rule `n_tokens = 13 * ceil(audio_seconds)` the 654.6 s row costs 8,515
speech tokens — an order of magnitude above the folds' worst rows (39.6 s and 53.8 s) — so the curve
cell cannot inherit whatever geometry the folds' prompt fit derives. The prompt fit re-derives both.

## Neither a probe-sample view nor a D1 media supplement is needed, and neither may be written

Section 7 priced Option A as costing "a new probe-sample-free subset receipt and its own D1 media
supplement". Measured against the committed receipts, it costs **neither**, and writing the first
would be a defect rather than a cost:

| gate | state | source |
|---|---|---|
| `data.audio2tool` sample universe | **400 / 400 already resolve** | `a2t-tier3467-official-population-2000` 196, `a2t-tier258-official-population-1500` 143, `a2t-tier1-official-population-500` 49, `r1-audio2tool-sample` 8, `select-fill-agentloop-104-postseal-scoring` 4 |
| D1 identity closure (I-4) | **400 / 400 already bound** | `d1-a2t-org1-union-4000.json` 392, the immutable `d1-identity.json` 8 |

`data.audio2tool._resolve_items` refuses a sample id that two probe-sample receipts claim, so an
additive view for this roster would not add a row — it would break the loader outright for every
Audio2Tool cell. `contracts.gate_media_identity` accepts exactly one supplement path per run and
verifies only the samples the binding names, so the curve cell configures the union's own
supplement (`receipts/artifacts/d1-a2t-org1-union-4000.json`, sha256 `b94439af…64ec59`); a 392-row
subset copy would re-bind identities that supplement already binds and close no gate it does not
already close. The builder asserts both facts fail-closed and refuses to write if either is false.

## What the builder verified before it wrote a byte

* the union flight-roster receipt hashes to `e5a81b71…857b8736`, the value its own committed dataset
  fragment `configs/dataset/audio2tool-org1-union-4000.json` pins, and **both** of its identity
  hashes reproduce from its items;
* the drawn subset's media facts, **measured** from the files on disk by
  `analysis.a2t_evo_capacity.measured_media_facts` (wav bytes re-hashed, wav headers read for frames
  and sample rate, tier-7 bound to the FIRST user turn as the official protocol serves it), agree
  with the union receipt's own records to the byte on `audio_sha256`, exactly on `media_relpath` and
  to 1e-6 on `audio_seconds`. Any disagreement means the D1 supplement this cell configures does not
  describe these bytes, so it is a refusal rather than a warning;
* `flight_roster_document` re-derives the flight identity from the items and refuses a disagreement
  with the frozen roster, and the roster's `gate_exposure_identity_hash` — what
  `contracts.gate_exposure` recomputes — equals `freeze_roster`'s own `split_identity_hash`;
* `canonical_receipt_bytes` reproduces the written file byte for byte.

## Exposure: the union is a fixpoint

Adding `docs/receipts/rosters/a2t-evo-curve-400-v1.json` — a `roster_role = "evaluation"` receipt,
therefore a genuine exposure source — leaves the Audio2Tool exposure union at **5,279 identities**
over **15 sources** instead of 14, because all 400 of its ids were already inside it through the
three official-population probe-sample receipts. Re-verified with
`rails.knowledge_build_a2t._exposure_sources` after the receipt landed. The V2 fold draw, which
excludes that union, is therefore unchanged by this row.

## Boundary

Wav bytes hashed and wav container headers read for frame count and sample rate; no decoding beyond
the header. The released tier manifests read for `id`, `path` / `chat_history` turn `path` and
`role`, and `domain` for **aggregate** strata counts only. No query text, no `tool_name`, no
`expected_tool_call`, no `functions`, no `instruction`, no annotation, no prior output and no score
is opened. No frozen core, tokenizer, embedder, retriever, scorer, network, GPU or paid API.
`CUDA_VISIBLE_DEVICES` empty throughout; `arm_offline_guard()` armed before the first input was
opened and recorded 0 outbound connection attempts against 0 targets.

This receipt grants no contact authority. The curve READS are separately registered under
`SAEA-A2T-EVO-A1-CURVE-400-V1`.
