# P-EMB-3M flight archive — SAEA-PROBE-pemb3m-388

**FLOWN 2026-08-20. No result was read.** Registration:
`docs/readiness/2026-08-20-pemb3m-preregistration-REGISTERED.md`. Identity basis:
`docs/readiness/2026-08-20-e1-local-embedder-identity.md`. Profile
`bounded-discovery-probe`. Study commit at takeoff `d0ea848`, tree clean and HEAD frozen for the
whole flight.

This directory holds receipts, session logs, manifest **summaries** and the launcher sources. It
holds **no vectors**: every `.npy`, every `vectors-*.jsonl` and every raw gate/jitter vector stays
under `$SPEECHRL_DATA_DIR`, exactly as the registration requires ("vectors on the data root, hashed
manifests only in Git"). A leak guard in `launcher/archive.sh` refuses the archive if any of them
appear here.

## Outcome in one table

| Arm | Model | Contacts | Dim | Result |
|---|---|---|---|---|
| M1 PRIMARY | `lco-embedding-omni-3b-gguf` (llama-server, `--pooling last`, mmproj) | 78/78 | 2048 | flown |
| M2 CONTROL (audio-TYPE) | `glap` (in-process transformers) | 78/78 | 1024 | flown |
| M3 CONTROL (speaking-STYLE) | `clsp` (in-process transformers) | 0 | — | **DROPPED-RUNTIME-ERROR** |
| M4 CASCADE | `qwen3-embedding-0.6b-gguf` (llama-server, text-text) | 78/78 + 2 jitter | 1024 | flown |

234/234 scored contacts across the three flyable arms, 0 failures, 0 replays. Every query/label
vector is distinct; the sweep-total invariant passed on the on-disk product.

## The four pre-flight gates (registration §3)

**(a) POOLING-DIFFER — `pooling_override_present = true`.** The single most consequential finding
of this flight. One synthetic, non-corpus 2 s 440 Hz sine clip was embedded under two SEPARATE LCO
boots, `--pooling mean` and `--pooling last`, and the two 2048-dim vectors are **byte-identical**
(both `e2be3465…4ead`). The CLI flag is demonstrably parsed — the `--pooling mean` boot logs
`model default pooling_type is [-1], but [1] was specified` — yet it does not change the pooled
AUDIO embedding at all. Per registration §4 this substitutes the **scoped** verdict names: an
LCO weak result is `EMB-WEAK-SCOPED` (scoped to this llama.cpp construction), never a model-level
refutation of the dedicated-embedder hypothesis. This is the same pathology the P-EMB-3L verdict
mandated checking for, now reproduced on a second, entirely different model.

**(b) Control import feasibility — EXTENDED per the 2026-08-20 coordinator amendment.** As shipped
the gate only sanity-embeds the TEXT side, leaving 156 scored M2/M3 contacts exposed to an
audio-path failure discovered mid-arm. It was extended at runtime to push one synthetic,
non-corpus clip through each control's AUDIO path as well.

- **GLAP: OK on both sides** (text dim 1024, audio dim 1024) → M2 flyable.
- **CLSP: DROPPED-RUNTIME-ERROR** → M3 not flown, audio side never reached.
  `AttributeError: 'CLSPModel' object has no attribute 'all_tied_weights_keys'`. CLSP's pinned
  remote code declares `transformers_version 4.57.3`; the shared venv is transformers **5.12.1**,
  whose `PreTrainedModel` requires that attribute. The weights load and the failure comes after,
  in v5's weight-tying bookkeeping. This is a version incompatibility of a **present** dependency,
  not a missing one, so it is deliberately NOT labelled `DROPPED-DEPS`. Nothing was installed,
  downgraded or patched: forcing a frozen third-party CONTROL past a version check would be an
  undisclosed instrument modification, and the registration is explicit that "a dropped control
  never blocks M1/M4".

**(c) Cascade source check — COMPLETE.** 60/60 T0 self-transcripts located among the CONSUMED
`SAEA-PROBE-pkey2-338` artifacts, registry sha256 `f8f6426a…4959` matching the machinery's pin.
Re-verified a second time at M4 entry. The `CASCADE-T0` supplement therefore **never flew**: zero
frozen-core generation contacts were spent by this flight.

**(d) Encode-only machine check — PASS** over `rails.embedding_client`,
`rails.local_encoder_client` and `rails.probes.pemb3m_flight`.

## Repeat-call determinism (registration §6)

- **LCO (`lco-last`, AUDIO path): byte-identical.** LCO's pooled audio embedding is bit-exact
  across identical GPU calls.
- **qwen3-emb (`qwen3-emb`, text): NOT byte-identical.** Reproduces E-1 Mission C's finding that
  qwen3-emb is not bit-exact across identical CUDA calls; the pair is persisted into M4's own
  manifest `jitter` side so the read suite can evaluate the declared cosine ≥ 0.9999 tolerance.

Both are recorded here as sha256 equality only. Cosine is a read-side computation and this flight
never performed one. The `lco-mean` gate boot carries no pair of its own (it exists solely to
produce the one vector the byte-compare needs); M2/M3 are in-process and have no server session.

## Spend

Two attempts on one registered row; spent contacts never un-spend.

| | calls | metered speech-audio s | GPU-h |
|---|---|---|---|
| attempt 1 `…110419Z-d6c576` (ABORTED) | 5 | 4.000 | ~0.065 (see below) |
| attempt 2 `…112943Z-410bdb` (FINALIZED) | 241 | 372.519 | 0.0329 |
| **total** | **246 / 440 registered** | **376.5 / 900** | **~0.098 / 0.5** |

Attempt 2's 241 = 234 scored + 7 gate contacts (2 GLAP sanity, 2 pooling-differ, 1 LCO
determinism, 2 M4 jitter). Metered audio is two passes over the frozen 60 (M1 and M2, 182.259 s
each) plus 8 s of synthetic non-corpus gate clip; M4 is text-only.

### Attempt 1 and why it was aborted

Attempt 1 spent 5 calls and produced no arm. In order: one GLAP text contact failed on a
device-placement bug; one call was over-charged by a launcher accounting bug and never issued; two
GLAP gate contacts succeeded; one LCO audio gate contact failed on llama.cpp's embedding-mode batch
clamp. Three distinct defects were found and fixed, all of them in the launcher or in how a
third-party model is driven — **never in the committed machinery, which flew unmodified**:

1. **GLAP device placement.** GLAP's own `encode_text` builds its token tensors on CPU
   unconditionally and moves only the encoder OUTPUT to the projection's device, i.e. upstream
   intends the SONAR text tower to stay on CPU while the audio tower runs on the GPU. A blanket
   `.to("cuda")` broke that contract. Fixed by restoring it — a device choice, not an edit to any
   pinned byte.
2. **Over-charging.** The gate pre-charged one call per control before issuing any, so a raise in
   the first control charged for a second contact that never happened. Fixed by charging inside the
   call path (`ChargingControlClient`), so durable spend equals contacts actually attempted.
3. **Embedding-mode batch clamp — the protocol amendment.** llama-server logs
   `embeddings enabled with n_batch (2048) > n_ubatch (512) / setting n_batch = n_ubatch = 512`
   and then refuses every audio contact:
   `input (1502 tokens) is too large to process. increase the physical batch size`. A pooled
   embedding needs the whole sequence in one physical batch, and LCO's qwen2.5o projector pads any
   clip to a ~30 s chunk (~1500 tokens) however short the utterance is. E-1's Mission-B
   verification ran on CPU and never exercised an audio contact under this clamp. The server recipe
   therefore gains `-b 4096 -ub 4096 -np 1`.

Because (3) changes the server recipe it changes the config hash, and therefore the `protocol_hash`
attempt 1's `ExecutionPlan` was bound to. Rather than fly under a protocol hash the plan never
carried, attempt 1 was durably ABORTED with that reason and a successor was opened. Its evidence is
archived here under `attempt1-aborted-*`, following the P-EMB-3L precedent. Attempt 1's GPU time
(232.4 s of LCO residency plus the GLAP load) was measured into its flight state but never reached
its durable `gpu_seconds` field, which reads 0.0 — an accounting gap in the aborted attempt, not
unmetered spend, since calls and audio were persisted BEFORE every send.

## Gate scope: a TOOL-contact flight

The frozen Qwen3-Omni core is **never loaded**. Only its pinned llama.cpp binary is reused, to serve
two different embedder GGUFs. The gate checks that genuinely apply were run explicitly and
individually — plan validation, exposure pre-registration, carrier scope, E0 closure + scoring
freeze, llama.cpp runtime-library verification — rather than through
`FrozenCoreGate.assert_model_touch_allowed`, whose remaining step (`_validate_runtime`) would
attest the 18 GB q4km GGUF set this flight never touches. What replaces it is stronger here, not
weaker: every GGUF byte actually served was fully SHA-256'd in preflight, cross-checked against the
umbrella lock wherever the lock carries a per-file hash, and pinned into the config hash the plan's
`protocol_hash` is computed from. `lco-embedding-omni-3b-gguf`, `glap` and `clsp` are
`LOCAL_CANDIDATE` lock entries with no per-file hash, so this flight self-pins them and says so;
`qwen3-embedding-0.6b-gguf` carries a real lock hash and it AGREED.

## Identity

- config hash = protocol hash `3ae99c9a7c943d016781c88bb1a5d256f86a9369d7c80ad6b0592b637f8d15a4`
- binding config sha256 `307e6828…6d3a` — recomputed live and matched the machinery's pin at
  import, preflight and every stage entry, so no arm binding or lock content could drift mid-flight
- split identity `fc9de436…5ee5`, verbatim from the machinery pin
- umbrella lock sha256 `9064bde8…71b1`
- llama.cpp build `5d9dfcb58ea860295da8fc93c7b5bed9e2c71151` (`llama.cpp-featcache`), binary
  re-hashed fail-closed by `core.session.start_session` at every one of the three spawns
- M1's feature cache is its OWN directory, `/home/chao/feat-cache/slurp-lco3b`: LCO's audio encoder
  is not q4km's, so a q4km-warmed feature must never be replayable for an LCO encode

## What this flight did NOT do

No cosine, no argmax, no ranking, no accuracy, no per-arm verdict, no cross-arm comparison.
Scoring-side gold was never loaded. The two byte-level comparisons recorded above (POOLING-DIFFER
and the determinism samples) are instrument-health facts the registration itself mandates. The
exposure row stays `consumed = no`; the single registered one-shot read
(`analysis.pemb3m_read`) has not happened.

## Files

`flight-receipt.json` (the machine record), `flight-state.json` (per-stage accumulation),
`execution-plan.json`, `config-values.json`, `attempt-state.json`, `embedding-manifest-summary.json`
(per-arm counts, dims and per-vector sha256 — no components), `flight.log` (both attempts),
`preflight-pytest.log` (3245 passed / 9 skipped at `d0ea848`), three `session-*.receipt.json` +
`session-*.server.log`, the `attempt1-aborted-*` set, and `launcher/` (the full instrument).
`MANIFEST.sha256` covers every file here.
