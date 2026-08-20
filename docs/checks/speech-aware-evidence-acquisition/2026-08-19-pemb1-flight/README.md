# P-EMB-1 embedding scenario routing — FLIGHT RECEIPT (Run A, 2026-08-19)

Registered probe `SAEA-PROBE-pemb1-78`, execution profile `bounded-discovery-probe`.
Preregistration: `docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md` (Run A, section 2).
Machinery: `rails.embedding_client` + `rails.probes.pemb_flight.run_pemb1_flight`
(flown at study commit `12d9795`, tree clean throughout).

**This run produced no read.** Embedding vectors are this flight's own product and were written to
the data root under a hashed manifest, but nothing here ever compared two of them: no cosine, no
argmax, no ranking, no accuracy. That is the separately-registered one-shot read mission's job
(`analysis.pemb_read run-a`). Everything in this directory is operational or structural: contact
counts, dimensions, latencies, hashes, cost, and the manifest's per-entry sha256 index.

| Field | Value |
|---|---|
| Run id | `SAEA-PROBE-pemb1-78` |
| Attempt | `attempt-20260819T235907Z-49567c` |
| Status | `COMPLETED` (error `None`); durable attempt state **`FINALIZED`** |
| Run dir | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb1-78/attempt-20260819T235907Z-49567c` |
| Study commit | `12d9795`, tree clean at takeoff and at finalize |
| Split identity | `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` (the SAME frozen 60 SLURP devel samples the consumed P-SLU/P-KEY/P-TRAP/P-FEW flights used) |
| Config hash | `d9a0c1a8874c961d60fe1b0cc6d9e222e6d91581c3c29101ffcb91197742f1bf` |
| Protocol hash | `97cf0d66190febf2a0519befe0b5c4731ae373deabb7b90b6775ca5e05c984f0` |
| Umbrella lock sha256 | `ad71f96732a2b69fb741b4fed4fe60fb1978dc23eb55522ce3943702f0801d1e` |
| Embedding dim | 2048 (pinned `rails.embedding_client.EMBEDDING_DIM`) |

No committed `configs/probes/g0-binding` flight config exists for this probe, for the same reason
the archived P-A2T whole-population launcher records: the registration wave landed the
preregistration, the machinery and the pinned read suite without one, and a flying agent must not
create one mid-session. Every identity and budget value came from an already-committed place —
machinery module constants, the frozen sample manifest and roster table, and the exposure row's own
registered ceilings. See `launcher/flight_identity.py`.

## 1. What was embedded

| Kind | n | Content | Source |
|---|---|---|---|
| `audio` | 60 | the frozen devel samples' RAW flac bytes, base64'd, behind the media marker — **bare, no prompt text** | `configs/probes/g0-binding/pslu-sample-devel-n60.json` via `pslu_flight.select_pslu_samples` |
| `text` | 18 | the canonical scenario labels as **bare label strings** (`alarm` … `weather`) | `configs/probes/g0-binding/pslu-rosters-train-only.json` via `pslu_s2_flight.canonical_scenario_labels` |

78 contacts total, **ZERO generation**. E-0's binding decision that **no instruct prefix** goes on
either side is structural here rather than merely observed: `EmbeddingClient.embed_text` sends
`{"content": [<the bare string>]}` and `embed_audio` sends
`{"content": [{"prompt_string": <marker>, "multimodal_data": [<base64>]}]}` — there is no seam in
the client through which a prefix, or any sampling parameter, could enter a request.

Audio payload profile measured in the pre-flight: total 182.26 s, min 1.41 s, mean 3.04 s,
max 6.21 s; media bytes min 27,333 / mean 57,300 / max 109,923.

## 2. The embedding server (NOT the generation server)

`rails.embedding_client.GENERATION_COEXISTENCE_NOTE`: an embedding-mode `llama-server` can never
coexist with a generation-mode one. This run therefore took its own sequential session on its own
port, after the P-FEW generation server had been torn down and verified gone.

| Field | Value |
|---|---|
| Port | **8091** (the generation port 8080 is never touched) |
| argv | `-c 49152 -np 1 -fa on -ngl 999 -ctk q8_0 -ctv q8_0 --embedding --pooling mean` |
| Binary | `llama.cpp-featcache/build/bin/llama-server`, sha256 `097c96ec…c68` (receipt pin) |
| Model files | the pinned q4km GGUF `0751c279…` + mmproj `f0dfe825…` (receipt pins) |
| Spawn + load | 15.1 s |
| `/props` `build_info` | `b5-5d9dfcb58` |
| `/props` `model_path` | the pinned q4km GGUF |

Two deltas from the committed model fragment beyond the standard three, both documented in
`launcher/flight_identity.py`: `--embedding --pooling mean` appended (the E-0 binding decision,
quoted verbatim in the preregistration's opening paragraph) and `-np 4` → `-np 1` (embedding mode
pools one sequence per request and contacts are issued strictly sequentially, so slots 2–4 could
never be used; memory-neutral, since total `n_ctx` is unchanged). `-c`, `-fa`, `-ngl`, `-ctk`,
`-ctv` are the committed fragment's own values. `--embd-normalize` was left at its default of `2`
(L2), which is the registration's own "L2-normalized outputs (cosine = dot)".

What the server itself reported (`postflight.log`, from its own log):

```
llama_server: embeddings enabled with n_batch (2048) > n_ubatch (512)
llama_server: setting n_batch = n_ubatch = 512 to avoid assertion failure
llama_init_from_model: model default pooling_type is [-1], but [1] was specified
slot load_model: id 0 | task -1 | new slot, n_ctx = 49152
```

This is exactly the "forced n_batch 512" behaviour E-0 recorded. Every pooled sequence in this run
sat far inside that budget (max clip 6.21 s), and all 78 contacts succeeded. The
`embeddings required but some input tokens were not marked as outputs -> overriding` notice appears
60 times — once per audio contact — and is llama.cpp's normal non-causal pooling path.

### Media marker

`LLAMA_MEDIA_MARKER` was pinned via env to `<__media__>` and then **re-verified fail-closed against
the live server's own `GET /props` `media_marker` field** before the first contact
(`EmbeddingClient.verify_media_marker`; a missing field or a mismatched value refuses outright and
never falls back to trusting the env). `marker-probe.log` is the model-free evidence that the value
is the pinned build's own default rather than a guess: `strings libmtmd.so` in the receipt-pinned
build carries exactly `<__media__>`, and the `media_marker` field name is present in
`libllama-server-impl.so`.

## 3. Contacts

| Field | Value |
|---|---|
| Contacts | **78 flown, 0 replayed, 0 failed** |
| By kind | `{"audio": 60, "text": 18}` |
| Dimensions | every vector 2048; dim distribution `{2048: 78}` |
| Mean latency | audio 0.085 s, text 0.013 s |
| Throughput | ~620 contacts/min at the end of the run |
| Flight wall | 7.55 s; GPU-occupied 0.4 min (22.68 GPU-seconds, durably recorded on the attempt) |

Every contact's spend was persisted to the durable attempt file **before** the request left the
process, and every contact was checked against the plan ceiling (including sibling attempts'
persisted spend) first — the `core.model.adapter.FrozenCoreAdapter` discipline, reimplemented in the
launcher because the embedding tier has no adapter. The gate ran first and in full:
`FrozenCoreGate.for_study_repo(...).assert_model_touch_allowed(plan)` (plan/scope validation,
exposure pre-registration match, carrier scope, E0 closure + scoring freeze, runtime receipt +
binary + GGUF bytes), followed by `assert_no_conflicting_generation_server`.

## 4. Vector manifest (structural only)

`rails.probes.pemb_flight.write_embedding_manifest` wrote one fp32 `.npy` per contact plus a hashed
`manifest.json` under `$SPEECHRL_DATA_DIR/derived/embeddings/SAEA-PROBE-pemb1-78/`. Derived
artifact: it stays on the data root and never enters Git. `embedding-manifest-summary.json` in this
directory is its STRUCTURAL index (contact id, kind, relpath, dims, sha256 — no vector component).

| Quantity | Value |
|---|---|
| Schema | `saea-pemb-embeddings-manifest-v1` |
| Entries | 78 (`audio` 60, `text` 18) |
| `.npy` files present | 78/78, every one 8,320 bytes (2048 × fp32 + npy header) |
| Distinct contact ids | 78 |
| **Distinct vector sha256** | **78** — no two vectors are byte-identical, so nothing collapsed to a degenerate constant |

That last row is the only "did the model actually do something" check performed here, and it is a
byte-identity count, not a similarity measurement.

## 5. Spend against the registered ceilings

| Column | Planned | Spent | Registered ceiling | Headroom |
|---|---|---|---|---|
| Core calls (embedding contacts) | 78 | **78** | 90 | 12 |
| Metered speech-audio seconds | 400 | **182.259** | 400 | 217.741 |
| GPU hours | 0.2 | **0.006** | 0.2 | 0.194 |

Embedding contacts ARE frozen-core contacts (encode+pool, zero sampling) and are ledgered as calls,
exactly as the preregistration's section 4 requires. Prior durable spend on this run id was 0 at
takeoff. A TEXT contact meters zero speech audio; because the durable store's `record_usage` API
refuses a non-positive audio figure, text contacts were charged a documented sentinel of `1e-9` s —
18 of them sum to 1.8e-8 s, and the durable actual audio figure (182.259 s) is the audio contacts'
real total to the millisecond.

## 6. Hygiene evidence

- **Runtime pins**: llama.cpp build commit `5d9dfcb58ea860295da8fc93c7b5bed9e2c71151`; binary sha256
  and both GGUF files match their receipt pins on byte count and sha256 (`gguf-verify.log`).
- **Feature cache**: `/home/chao/feat-cache/slurp-q4km` held 63 entries before and 63 after — the
  embedding-mode encoder pass was served from the SAME cache the generation flights warmed over
  these same 60 clips. The legacy `q4km` cache (34,350 entries) and `audio2tool-q4km` (490 entries)
  were untouched.
- **Coexistence**: the P-FEW generation server was torn down and verified gone (ports 8080/8091 both
  unbound, GPU at 18 MiB) before this run started; the launcher re-checked port 8080 itself and
  refused-on-reachable. After the run the embedding server exited with its launcher and the GPU
  returned to 18 MiB.
- **D3 gate**: `PYTHONDONTWRITEBYTECODE=1` throughout; zero `__pycache__`/`*.pyc` under the frozen
  scoring package.
- **Suite**: the full suite ran once at session start — **3008 passed, 9 skipped**
  (`preflight-pytest.log`).
- **Tree**: clean at `12d9795` at takeoff and at finalize.

## 7. Why two embedding sessions rather than one

The session plan allowed Run A and Run B to share one embedding server. They do not, and the reason
is `docs/featcache-directories.md`: the feature-cache directory is `<dataset>-<encoder>`, one per
dataset campaign, and it reaches the server through `server_env`, which is fixed at spawn time. One
shared session could only ever point at one dataset's cache directory, so Run A took
`slurp-q4km` and Run B takes `audio2tool-q4km` in a second, sequential session with its own session
receipt. Both are embedding-mode, neither ever coexisted with a generation server, and the teardown
between every session is recorded in `session-teardown.log`.

## 8. Files

| File | What it is |
|---|---|
| `README.md` | this receipt |
| `launcher/` | every file that produced the run (env, identity, pre-flight, launcher, post-flight, wrappers, session teardown, marker probe) |
| `session-precheck.log` | session-start environment probe (GPU, caches, orphans, disk) |
| `preflight-pytest.log` | the full suite, run once for all three probes in this session |
| `marker-probe.log` | model-free binary evidence for the `LLAMA_MEDIA_MARKER` pin |
| `session-teardown.log` | every llama-server teardown in this session, with the GPU state after each |
| `preflight.log` | pre-flight (split identity, counts, audio profile, ledger, budgets, argv, marker pin, coexistence) |
| `gguf-verify.log` | binary + per-file GGUF sha256 against the runtime receipt |
| `flight.log` | operational flight log (contact index, kind, contact id, latency, dims only) |
| `postflight.log` | post-flight structural verification |
| `flight-receipt.json` | the launcher's own receipt (identity, cost, contact counts, gate diagnostics, session pins) |
| `execution-plan.json` | the validated `ExecutionPlan` |
| `config-values.json` | the hashed config values bundle |
| `session-receipt.json` | the embedding-mode llama-server session receipt |
| `attempt-state.json` | the durable attempt file (state machine + persisted actual spend) |
| `contacts.json` | per-contact record from the client itself (id, kind, timestamp, latency, dims) |
| `embedding-manifest-summary.json` | STRUCTURAL index of the vector manifest (per-entry sha256/relpath/dims). The vectors themselves stay on the data root, never in Git |
| `MANIFEST.sha256` | sha256 over every file above |
