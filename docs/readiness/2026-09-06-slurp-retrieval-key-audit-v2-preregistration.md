# MF-7b — the SLURP retrieval-key audit, GPU part: omni-embedding speech-to-text matching

**Preregistration. Written and committed BEFORE the first embedding contact and before any v2
number exists.** Successor to `docs/readiness/2026-09-06-slurp-retrieval-key-audit-v1.md`
(MF-7, CPU part), whose section 6 prepared these steps and did not run them.

Authority: owner GO 2026-09-06 (MF-7), the owner rule of 2026-09-06 that **the retrieval query
must contain the speech signal**, and the owner restriction of 2026-09-06 that the GPU part is
scoped to **omni-embedding speech-to-text matching** — no featcache audio-to-audio experiment, no
transcript of any kind, no `pip install`, no ffmpeg, no venv change.

Exposure rows, all three registered in `docs/exposure-ledger.md` before the first contact:

* `SAEA-SLURP-MF7B-LCO-EMBEDDING-V1` — the LCO-Embedding-Omni-3B encoder pass (tool contacts);
* `SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1` — the Omni-Embed-Nemotron-3B encoder pass (tool
  contacts);
* `SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V2` — the model-free read that consumes the new vectors and
  the sealed data, cites V1, and applies the decision table below.

Profile `model-free-check` for the audit row; the two encoder rows are tool-level contacts under
the frozen tool-level retriever/judge clause. **Zero frozen-core contacts in all three.**

## 1. What this part asks, and what changed since V1

V1 measured four query sets on CPU and found: a GLAP speech query is catastrophic as a retrieval
key (−32.60 pp net corrective power on NEW500), the one set that cleared the gate cleared it by
echoing its own input (96.19 % echo), and the **gold-text ceiling is +13.00 pp** — so the loss is
cross-modal, not inherent to neighbour voting. V1's own section 5.6 named the follow-on precisely:

> a speech encoder is a candidate only if it closes a meaningful share of the 10.60 pp cross-modal
> gap *with the prior dimension switched off* … and discount any gain whose echo rate is near 100.

This part runs that test with two omni embedders that were built for speech-to-text matching.

**Three things changed and are fixed here before any result is read.**

1. **The comparator was re-locked on 2026-09-06.** Corrective power is now measured against the
   sealed closed-list arm **plus `slurp-legal-label-projection-v2`**, scored through the registered
   `slurp-slu-official-projected-v2` (`docs/readiness/2026-09-06-slurp-legal-label-projection-v2-verdict.md`).
   Published levels this read must reproduce exactly, as its identity anchor, before any new number
   is trusted: **intent 73.10 pooled, 75.20 NEW500, 71.00 OLD500** (V1's unprojected mask was
   71.40 / 73.20 / 69.60, and every V1 net figure is stated against that older mask). NEW500 under
   the re-locked comparator therefore has **376 right rows to harm and 124 wrong rows to save**.
   If the reconstructed per-row mask does not reproduce all three published levels to the second
   decimal, the read STOPS and reports the mismatch instead of a verdict.
2. **A second key space is measured.** Beside the 11,514 TRAIN utterance texts, the same queries
   are matched against the **60 intent label descriptions** of the closed-list inventory
   (label-space matching). This is reported separately and never decides this gate (clause 6).
3. **Cross-modal separation is reported.** For every speech set, the cosine distribution of
   matched pairs (key intent equals the DEV row's gold intent) against unmatched pairs, so a
   negative result can distinguish "the encoder puts speech and text in different places" from
   "the ranking is too weak for a majority vote".

## 2. Query sets, key sets, and what is a candidate

**Queries** — the DEV-1000 roster, split identity `8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84`,
1,000 rows, NEW500 the decision population. Per embedder E ∈ {`lco`, `nemotron`}:

| query set | signal | shape | role |
|---|---|---|---|
| `q-speech-E` | speech alone | the DEV recording, E's own audio path | **candidate** |
| `q-speech-E+state` | speech + state, RANK level | the same vectors, fused by the registered ranker `saea-rank-wcos-prior-agree-v1` with the sealed draft's intent as the prior, exactly as V1 | **candidate** |
| `q-speech-E-fused` | speech + state, INPUT level | the recording and the sealed KU-S1c phase-1 draft response text as ONE multimodal input to E | **candidate** |

The "state" is the sealed KU-S1c phase-1 draft response text of run
`SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1`, attempt `attempt-20260906T042946Z-44720f` — the same
bytes V1's `q-draft` embedded. It is the agent's own intermediate state, available at retrieval
time; it is never a transcript and never gold.

**Carried forward from V1 at zero new contacts**, re-measured against the re-locked comparator so
one table can be read end to end: `q-speech-glap`, `q-speech-glap+state` (candidates, GLAP),
`q-draft` and `q-gold-text` (**diagnostics, never eligible**, enforced in
`analysis.slurp_retrieval_key_audit.DIAGNOSTIC_ONLY`). No GLAP vector is recomputed; the sealed
V1 JSONL files are reused byte for byte and re-hashed before use.

**Key set (a) — TRAIN utterance texts.** The 11,514 TRAIN content facets of snapshot
`e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57`, one per TRAIN utterance, the
utterance text as the key representation, each carrying its TRAIN gold intent and gold
`{type, filler}` slots. Re-embedded by each speech encoder with that encoder's own text tower,
because a query may only be compared against keys embedded by the same encoder.

**Key set (b) — the 60 intent label descriptions.** One key per legal `(scenario, action)` pair of
the closed-list inventory (`data.slurp.render_slurp_label_inventory`'s own 60 pairs). The key text
is fixed here, before it is built, as rule **`saea-mf7b-label-text-v1`**: for intent
`(scenario, action)` the text is `f"{scenario} {action}"` with every `_` replaced by a single
space, lower-case, no other edit. It is the label itself in words — no invented gloss, no example
filler, no description written by this agent. A label key carries its own intent and **no slots**,
so filler recall is undefined on key set (b) and is reported as `null` rather than as zero.

## 3. Protocol

Identical to V1 section 3 except where section 1 above changes it, and nothing else moves:
cosine top-k over the complete key set, k ∈ {1, 5, 10}, ties broken by ascending key id; intent
recall@k, majority vote accuracy@k, corrective power (saves among comparator-wrong rows, harms
among comparator-right rows, net = saves − harms in rows and in pp), filler recall@k over rows
with at least one gold slot, echo rate against the sealed draft's own label; NEW500 / OLD500 /
pooled 1,000 and per gold scenario; stratified paired bootstrap, 10,000 replicates, seed 20260903,
strata = gold scenario, CI90, through this repository's single resampler
`analysis.paired.paired_contrast`. The `+state` rank fusion uses the registered weights unchanged
(`w_cos` 0.5, `w_prior` 0.3, `w_agree` 0.2 from `configs/policy/kb-policy-v1.json`) and adds no
knob; its closed-form dominance margin of 0.8 raw cosine is carried in the receipt again.

**Cross-modal separation**, new and non-gating: per speech query set, over all 1,000 × N key
cosines, the mean / sd / p05 / p50 / p95 of the matched population (key intent = gold intent) and
of the unmatched population, their difference, and the standardised separation
`(mean_matched − mean_unmatched) / sd_unmatched`. Reported for the text-key space and the
label-key space.

**Serving, fixed in advance.** LCO through the pinned featcache `llama-server --embedding
--pooling last` with `-ngl 999 -c 8192 -b 2048 -ub 2048 -np 1 -fa on`, one resident server, its
own port, the server's own randomised `media_marker` read from `GET /props` and re-verified by
`rails.embedding_client.EmbeddingClient.verify_media_marker` with `expected_dim=2048`; texts
batched, audio one per request; a jitter pair (one clip embedded twice) states whether the pass is
bit-exact. Nemotron through plain `transformers` on CUDA in bf16 with `attn_implementation="sdpa"`,
`Qwen2_5OmniProcessor`, mean pooling over the attention mask with `include_prompt: true`, L2
normalise, and the model's own contract prompts `"query: "` for DEV queries and `"passage: "` for
TRAIN text keys; `sentence_transformers` is NOT imported (it pulls `torchcodec`, which cannot load
`libavutil` because ffmpeg is deliberately absent and must never be installed). Only one embedder
is resident on the 24 GB card at a time. Audio is read with `soundfile`, never ffmpeg. If a loader
refuses, the exact error is reported and the other embedder continues alone.

## 4. The preregistered decision table

Decision k = 5, decision population NEW500, comparator as in clause 1 of section 1.

1. **Eligibility.** Only a speech-containing set may win. `q-draft` and `q-gold-text` are
   diagnostics and can never win, whatever their numbers.
2. **Degeneracy.** A set whose **echo rate at k = 5 on NEW500 is ≥ 90 %** is marked **DEGENERATE**
   and cannot be the winner that licenses KU-S1. Its vote is its own input rather than a retrieved
   neighbour; V1 section 5.6 already instructed this read to discount such a gain. A degenerate
   set is still measured and reported in every table.
3. **The winner** is the non-degenerate speech-containing set with the highest net corrective power
   on NEW500 against the re-locked comparator. Ties break in this order: speech alone before
   speech+state; input-level fusion before rank-level fusion; fewer models before more; then the
   set id ascending.
4. **The gate.** KU-S1 flies with that winner's `query_source` **iff its net corrective power is
   ≥ 2.00 pp AND its CI90 lower bound on NEW500 is strictly above 0.** Both conditions, not
   either.
5. **Otherwise the branch is CLOSED.** If no non-degenerate speech-containing set meets clause 4,
   **neighbour retrieval on SLURP intent is CLOSED** and re-scoped, in this note, to (a) the slot
   side as **KU-S3** — filler recall is the reading that survives, and KC-S1b already holds an
   admitted slot mechanism — and (b) **Audio2Tool as KU-A1**, with the same two embedders, with
   MF-6 to be measured with them. No further SLURP intent-retrieval cell is proposed.
6. **Label-space keys never decide this gate.** Key set (b) supplies a label, not a neighbour
   utterance; it is a different evidence object and would need its own cell. Its table is reported
   in full beside the text-key table, and if it beats the text-key winner that is recorded as a
   finding for a future preregistration, not as this gate's outcome.
7. **The cross-modal loss** is reported as `q-gold-text`'s net minus the winner's net, on the same
   comparator, exactly as V1 defined it.
8. **Filler recall@5 and the cross-modal separation are reported for every set and gate nothing.**
9. **One product only.** No admission, promotion, superiority, generality or Stage-3 claim follows
   from this note. If the gate is cleared, the product is one `phase_supply.evidence.query_source`
   block (relpath, sha256, `embedded_signal`) plus the matching facet-side consequence; if it is
   not, the product is the closure statement of clause 5.

**A property stated before the run, so it cannot be claimed as a finding afterwards.** The
rank-level `+state` fusion's dominance margin at the registered weights is 0.8 raw cosine, far
outside the range SLURP cosines occupy, so every `+state` set is expected to echo the draft's label
on essentially every row where the draft named a legal intent, whatever its encoder. V1 measured
96.19 % for GLAP. Clause 2 exists because of that arithmetic, not because of a v2 number.

## 5. Accounting registered in advance

Per embedder: 1,000 DEV speech queries + 1,000 fused speech+state queries + 11,514 TRAIN text keys
+ 60 label keys = **13,574 forward passes**, plus a stated margin of 26 for jitter pairs, probes
and retries — **13,600 registered tool contacts per embedder, 27,200 in total**, and **0
frozen-core contacts**. GPU hours are estimated at **≤ 1.5 per embedder, ≤ 3.0 in total**, and the
realised figure is measured and carried in each receipt; a pass that exceeds its estimate is
stopped and reported rather than extended silently. Speech seconds: the roster's own 2,884.7937 s,
traversed twice per embedder (speech alone and fused) = 5,769.5874 s per embedder. Paid API spend
0. The audit read itself makes 0 model, tool, embedding and network contacts and uses 0 GPU.

Vectors land under `SPEECHRL_DATA_DIR/vectors/slurp-mf7b/` in the same `saea-mf7-vectors-v1` JSONL
schema V1 used and never enter Git; each pass writes a `saea-mf7-vectors-receipt-v1` receipt
carrying counts, dims, sha256, bytes, L2 norms, wall time, throughput, the model fingerprint or
server `/props`, and the accounting block.

## 6. Boundaries carried

* The SLURP `test` split is never named, loaded, scored or embedded. Every loader call passes
  `allow_heldout=False`.
* **No devel sentence text is read in this part at all.** `q-gold-text` is NOT recomputed: its V1
  vectors are reused as sealed bytes, so the text ceiling is carried forward without reopening the
  text. No transcript of any kind is produced, embedded or supplied.
* TRAIN is construction data and is readable; the key side is TRAIN only.
* DEV-1000 is prior-exposed as a whole; NEW500 is the only unexposed half and is the decision
  population. No new evaluation surface opens.
* The frozen core is not contacted. Both embedders are tool-level, local, pinned, and their
  vectors are the whole product of their rows.
