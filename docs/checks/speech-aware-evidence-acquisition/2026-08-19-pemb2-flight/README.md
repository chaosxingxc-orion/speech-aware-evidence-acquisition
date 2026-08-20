# P-EMB-2 embedding tool routing — FLIGHT RECEIPT (Run B, 2026-08-20)

Registered probe `SAEA-PROBE-pemb2-552`, execution profile `bounded-discovery-probe`.
Preregistration: `docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md` (Run B, section 3 —
"the 183 headline"). Machinery: `rails.embedding_client` +
`rails.probes.pemb_flight.run_pemb2_flight` (flown at study commit `7aeeb2e`, tree clean throughout).

**This run produced no read.** Embedding vectors are this flight's own product and were written to
the data root under a hashed manifest, but nothing here ever compared two of them: no cosine, no
argmax, no top-1/top-5, no recovery count, and the 183/217 partition was never derived. That is the
separately-registered one-shot read mission's job (`analysis.pemb_read run-b`). Everything in this
directory is operational or structural.

| Field | Value |
|---|---|
| Run id | `SAEA-PROBE-pemb2-552` |
| Attempt | `attempt-20260820T002031Z-e816e2` |
| Status | `COMPLETED` (error `None`); durable attempt state **`FINALIZED`** |
| Run dir | `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pemb2-552/attempt-20260820T002031Z-e816e2` |
| Study commit | `7aeeb2e`, tree clean at takeoff and at finalize |
| Split identity | `e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c` (the SAME frozen 400-sample Audio2Tool discovery split the consumed A0 / a2t-pop / a2t-abst flights used) |
| Config hash | `4aa5ad30e2aafdb6a18dfa3dba70dffab75e858da90a719d8b9037bde7ec700f` |
| Protocol hash | `b4f4d4884ebdadc26106fb56ed5327d787d931cdb4c19c1d8b046b22aabe63d7` |
| Umbrella lock sha256 | `ad71f96732a2b69fb741b4fed4fe60fb1978dc23eb55522ce3943702f0801d1e` |
| Embedding dim | 2048 (pinned `rails.embedding_client.EMBEDDING_DIM`) |

The split identity was **not** re-derived: `flight_identity.split_identity_hash_for("B")` takes the
committed `rails.probes.a2t_pop_flight.SPLIT_IDENTITY_HASH`, cross-checks it against
`pemb_flight.EXPECTED_RUN_B_SPLIT_IDENTITY_HASH`, and then runs the machinery's own fail-closed
`assert_run_b_split_identity_hash` on it. Any disagreement refuses before a socket is opened.

## 1. What was embedded

| Kind | n | Content | Source |
|---|---|---|---|
| `audio` | 400 | the frozen discovery split's RAW wav bytes, base64'd, behind the media marker — **bare, no prompt text** | `Audio2ToolAdapter.load_split("discovery")` over the committed probe receipt |
| `text` | 152 | the tool registry rows in their **shipped rendering**, keyed by `tool_name` | `data.audio2tool.load_tool_registry` + `render_registry_row` (default form, `strip_defaults=False`) |

552 contacts total, **ZERO generation**, no instruct prefix on either side (structural — the client
has no seam for a prefix or a sampling parameter). Audio payload profile measured in the pre-flight:
total 2159.69 s, min 0.62 s, mean 5.40 s, max 35.71 s; media bytes min 29,654 / mean 259,202 /
max 1,714,304.

## 2. Pooled-sequence feasibility, settled before the contacts were spent

Embedding mode forces `n_batch = n_ubatch = 512`, so a pooled sequence longer than 512 tokens would
fail. Run B's longest clip is 35.71 s — long enough that this needed an answer rather than a hope.

Run A's own server log reported a per-request token count for each of its 60 audio contacts,
quantized as `2 + 13·k` with `k ∈ {2,3,4,5,6,7}` at multiplicities `{10, 24, 15, 7, 3, 1}`. Matching
those cumulative multiplicities against the frozen 60's own sorted durations brackets the encoder's
chunk length to

```
0.9983 s  ≤  c  <  1.0080 s        (13 tokens per ~1 s of audio)
```

Across that entire bracket, Run B's longest clip predicts **470 tokens** — inside 512 with 42 to
spare — and **zero** of the 400 clips exceed 512 even at the worst-case (smallest) `c`; the safe
ceiling at that end of the bracket is 38.93 s against an observed maximum of 35.71 s. The run was
therefore flown on E-0's recipe unchanged, with no batch-size delta invented for it
(`token-fit.log`, `token-rate-probe.log`). All 552 contacts succeeded, confirming the arithmetic.

This probe reads only llama-server's own operational log and the durations; no vector, no output row.

## 3. The embedding server (NOT the generation server)

Its own sequential session — the second of this session's two, after Run A's was torn down and
verified gone.

| Field | Value |
|---|---|
| Port | **8091** (generation port 8080 never touched; verified unreachable by the launcher) |
| argv | `-c 49152 -np 1 -fa on -ngl 999 -ctk q8_0 -ctv q8_0 --embedding --pooling mean` |
| Binary | `llama.cpp-featcache/build/bin/llama-server`, sha256 `097c96ec…c68` (receipt pin) |
| Model files | the pinned q4km GGUF `0751c279…` + mmproj `f0dfe825…` (receipt pins) |
| Spawn + load | 17.8 s |

The server's own log again confirms the recipe as-built:

```
llama_server: embeddings enabled with n_batch (2048) > n_ubatch (512)
llama_server: setting n_batch = n_ubatch = 512 to avoid assertion failure
llama_init_from_model: model default pooling_type is [-1], but [1] was specified
slot load_model: id 0 | task -1 | new slot, n_ctx = 49152
```

`LLAMA_MEDIA_MARKER` was pinned via env to `<__media__>` and re-verified fail-closed against the
live server's own `GET /props` `media_marker` field before the first contact.

## 4. Contacts

| Field | Value |
|---|---|
| Contacts | **552 flown, 0 replayed, 0 failed** |
| By kind | `{"audio": 400, "text": 152}` |
| Dimensions | every vector 2048; dim distribution `{2048: 552}` |
| Mean latency | audio 0.129 s, text 0.095 s |
| Throughput | ~438 contacts/min |
| Flight wall | 75.65 s; GPU-occupied 1.6 min (93.48 GPU-seconds, durably recorded on the attempt) |

The gate ran in full before the spawn (`FrozenCoreGate.assert_model_touch_allowed(plan)`), then
`assert_no_conflicting_generation_server`, then the durable attempt was opened atomically, and every
contact's spend was persisted **before** the request left the process and checked against the plan
ceiling including sibling attempts.

## 5. Vector manifest (structural only)

Written to `$SPEECHRL_DATA_DIR/derived/embeddings/SAEA-PROBE-pemb2-552/`. Derived artifact: it stays
on the data root and never enters Git. `embedding-manifest-summary.json` here is its STRUCTURAL
index (contact id, kind, relpath, dims, sha256 — no vector component).

| Quantity | Value |
|---|---|
| Schema | `saea-pemb-embeddings-manifest-v1` |
| Entries | 552 (`audio` 400, `text` 152) |
| `.npy` files present | 552/552, every one 8,320 bytes (2048 × fp32 + npy header) |
| Distinct contact ids | 552 |
| **Distinct vector sha256** | **552** — no two vectors byte-identical, so nothing collapsed to a degenerate constant |

That byte-identity count is the only "did the model do something" check performed here.

## 6. Spend against the registered ceilings

| Column | Planned | Spent | Registered ceiling | Headroom |
|---|---|---|---|---|
| Core calls (embedding contacts) | 552 | **552** | 600 | 48 |
| Metered speech-audio seconds | 3000 | **2159.688** | 3000 | 840.312 |
| GPU hours | 0.5 | **0.026** | 0.5 | 0.474 |

Prior durable spend on this run id was 0 at takeoff. Text contacts meter zero speech audio and were
charged the documented `1e-9` s sentinel (152 of them sum to 1.5e-7 s); the durable actual audio
figure is the 400 audio contacts' real total.

## 7. Hygiene evidence

- **Runtime pins**: llama.cpp build commit `5d9dfcb58ea860295da8fc93c7b5bed9e2c71151`; binary and
  both GGUF files match their receipt pins on byte count and sha256 (`gguf-verify.log`).
- **Feature cache**: `/home/chao/feat-cache/audio2tool-q4km` held 490 entries before and 490 after —
  the embedding-mode encoder pass was served from the SAME cache the A0 and Stage-2 generation
  flights warmed over these same 400 clips. The legacy `q4km` cache (34,350 entries) and
  `slurp-q4km` (63 entries) were untouched.
- **Coexistence**: Run A's embedding server was torn down and verified gone before this run started;
  the launcher re-checked the generation port itself. Afterwards no server is resident and the GPU
  is back to 18 MiB.
- **D3 gate**: `PYTHONDONTWRITEBYTECODE=1` throughout; zero `__pycache__`/`*.pyc` under the frozen
  scoring package.
- **Suite**: the full suite ran once at session start — **3008 passed, 9 skipped**
  (`preflight-pytest.log`).
- **Tree**: clean at `7aeeb2e` at takeoff and at finalize.

## 8. Why two embedding sessions rather than one

The session plan allowed Run A and Run B to share one embedding server. They do not, and the reason
is `docs/featcache-directories.md`: the feature-cache directory is `<dataset>-<encoder>`, one per
dataset campaign, and it reaches the server through `server_env`, which is fixed at spawn time. One
shared session could only ever point at one dataset's cache directory, so Run A used `slurp-q4km`
and Run B used `audio2tool-q4km`, each in its own sequential session with its own session receipt.
Neither ever coexisted with a generation server; every teardown is in `session-teardown.log`.

## 9. Files

| File | What it is |
|---|---|
| `README.md` | this receipt |
| `launcher/` | every file that produced the run (env, identity, pre-flight, launcher, post-flight, wrappers, session teardown, marker probe, feasibility probes) |
| `session-precheck.log` | session-start environment probe (GPU, caches, orphans, disk) |
| `preflight-pytest.log` | the full suite, run once for all three probes in this session |
| `marker-probe.log` | model-free binary evidence for the `LLAMA_MEDIA_MARKER` pin |
| `token-rate-probe.log` | Run A's own server-log token counts (operational log only) |
| `token-fit.log` | the chunk-length bracket and the 512-budget feasibility arithmetic for Run B |
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
| `embedding-manifest-summary.json` | STRUCTURAL index of the vector manifest. The vectors themselves stay on the data root, never in Git |
| `MANIFEST.sha256` | sha256 over every file above |
