# P-EMB-3L local embedding construction sweep — FLIGHT RECEIPT (2026-08-20)

Registered probe `SAEA-PROBE-pemb3l-234`, execution profile `bounded-discovery-probe`.
Preregistration: `docs/readiness/2026-08-20-pemb3l-preregistration-REGISTERED.md`. Machinery:
`rails.probes.pemb3l_flight` (coordinator-reviewed, flown UNMODIFIED) over the
`rails.embedding_client` prefix seam, at study commit `339e8ce`, tree clean throughout.

**This run produced no read.** Embedding vectors are this flight's own product and were written to
the data root under hashed per-arm manifests, but nothing here ever compared two of them: no cosine,
no argmax, no top-1, no accuracy, no per-arm verdict, and the LOCAL-SPACE-EXISTS / LOCAL-EXHAUSTED /
INCONCLUSIVE-EMB3L clause was never evaluated. That is the separately-registered one-shot read
mission's job (`analysis.pemb3l_read`). Everything in this directory is operational or structural.

| Field | Value |
|---|---|
| Run id | `SAEA-PROBE-pemb3l-234` |
| Attempts | `attempt-20260820T062543Z-e91099` (**ABORTED**, L1+L2) then `attempt-20260820T065009Z-1361ad` (**COMPLETED**, durable state **FINALIZED**, L3) |
| Contacts | **234 / 234**, 0 failures, 0 retries, 0 replays |
| Study commit | `339e8ce`, tree clean at both takeoffs and at finalize |
| Split identity | `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` (the SAME frozen 60-sample SLURP devel subset the consumed P-SLU/P-KEY/P-TRAP/P-EMB-1 probes used; never re-derived) |
| Config hash | `67091662a7c98389d787204b4fa282fba0a78f1d4690cf7c30c5e3d65a2df8a1` (identical across both attempts) |
| Protocol hash | `289397270e1eb5389bf9f907e323984fed546e07b19984bc5cd9139d59290a7c` (identical across both attempts) |
| Binding config sha256 | `fa698d31699314ecc94a046b8de4c664f7ea35ccab858f248d93b235d3ef8b15` — LIVE recompute equals the pinned constant |
| Umbrella lock sha256 | `9064bde89d4248fd80c9c2f93c2a9c276a454eadbb1aa7d529671118961371b1` |
| Embedding dim | 2048 (pinned `rails.embedding_client.EMBEDDING_DIM`) |

## 1. What was embedded

The P-EMB-1 surface reused verbatim — the frozen 60 SLURP devel audio samples and the 18 canonical
scenario labels — under three training-free constructions, 78 contacts each, **zero generation**:

| Arm | Pooling | Audio prefix | Text prefix | Contacts |
|---|---|---|---|---|
| `l1-last-bare` | `--pooling last` | *(none)* | *(none)* | 78 |
| `l2-last-instruct` | `--pooling last` | `Represent this utterance for intent retrieval: ` | `Represent this intent label for retrieval: ` | 78 |
| `l3-mean-instruct` | `--pooling mean` | *same as L2* | *same as L2* | 78 |

The two instruct strings are EXACT, trailing space included (the client concatenates prefix + payload
with no separator of its own); `assert_binding_config_sha256()` re-derived the arm table's digest and
matched the pinned `BINDING_CONFIG_SHA256` at module import, in the pre-flight, and again at both
takeoffs, so neither string nor either pooling mode could drift underneath a flight in progress.

Mean-bare is NOT re-flown: it is the cited constant `CITED_MEAN_BARE_ACCURACY = 0.0500` carried from
the consumed P-EMB-1 read. This flight neither used nor checked that number.

Audio payload profile (one pass): total 182.259 s, min 1.41 s, mean 3.04 s, max 6.21 s; media bytes
min 27,333 / mean 57,300 / max 109,923. Each arm re-embeds the same 60 clips, so the sweep meters that
one-pass total three times.

## 2. Two sessions, because pooling mode is a startup flag

A resident llama-server's pooling mode is fixed at spawn, never a per-request parameter, so L1+L2
(`last`) and L3 (`mean`) cannot share a session. `rails.probes.pemb3l_flight` tags each arm with its
required `pooling_mode` and performs no server I/O of its own; the launcher owns the sessions.

| Field | Session `last` | Session `mean` |
|---|---|---|
| Port | **8093** (generation port 8080 verified unreachable before each spawn) | **8093** |
| argv tail | `--embedding --pooling last` | `--embedding --pooling mean` |
| Server-reported pooling_type | `[3]` | `[1]` |
| Spawn + load | 25.1 s | 13.1 s |
| Arms flown | `l1-last-bare`, `l2-last-instruct` (attempt 1) | `l3-mean-instruct` (attempt 2) |

Common argv `-c 49152 -np 1 -fa on -ngl 999 -ctk q8_0 -ctv q8_0 --embedding`; binary
`llama.cpp-featcache/build/bin/llama-server` sha256 `097c96ec…c68`; the pinned q4km GGUF `0751c279…`
plus mmproj `f0dfe825…` (receipt pins, all re-verified — `gguf-verify.log`). Both server logs confirm
the recipe as-built: `embeddings enabled with n_batch (2048) > n_ubatch (512)` →
`setting n_batch = n_ubatch = 512`, and `new slot, n_ctx = 49152`.

`LLAMA_MEDIA_MARKER` was pinned via env to `<__media__>` and re-verified fail-closed against each live
server's own `GET /props` `media_marker` field **at the head of every arm** (the machinery calls
`verify_media_marker()` per arm, so three independent verifications). `marker-probe.log` carries the
model-free binary evidence that this literal is the receipt-pinned build's own mtmd default and that
this build accepts both `last` and `mean` for `--pooling`.

## 3. The abort, and why it cost no registered calls

Attempt 1 flew L1 (78/78, 12.5 s) and L2 (78/78, 11.0 s) cleanly, then **aborted in the launcher's own
inter-session teardown** — not in the machinery, not in the model path, and not in any registered
check. Recorded reason:

```
teardown failed: pid 6099 alive=True, port 8093 reachable=False
```

`port 8093 reachable=False` is the tell: llama-server had already taken SIGTERM and exited. The
defect was in the launcher's `_pid_alive`, which probed liveness with `os.kill(pid, 0)` alone. A
server this launcher spawns is a **child** of the launcher process, so on exit it becomes a
**zombie** until reaped — and `os.kill` succeeds on a zombie. The guard therefore read an exited
server as permanently alive, escalated pointlessly to SIGKILL, and refused the sweep rather than
spawn session 2 on top of what it believed was a resident server. Fail-closed behaved correctly on
a false premise.

Two repairs, both in the launcher (the reviewed machinery was not touched):

1. `_pid_alive` now reaps with `os.waitpid(pid, WNOHANG)` first, treats a `/proc/<pid>/stat` state of
   `Z` as dead, and only then falls back to the signal probe — the same `waitpid`-after-kill
   discipline the repository's own `tests/unit/test_session.py` spawn probe uses.
   `abort-repair-proof.log` reproduces the original bug directly (raw `os.kill(pid, 0)` → `True` on
   the zombie) and shows the repaired predicate returning `False`, idempotently.
2. **Arm-level idempotence.** Before flying an arm the launcher checks whether that arm's registered
   product is already complete on the data root (78 entries, 60 audio + 18 text, all dims 2048, all
   `.npy` present — structural only, no vector value read). A complete arm is **carried**, never
   re-flown, and a session whose arms are all carried is **never spawned**.

Because the attempt state machine makes ABORTED terminal (`record_usage` requires OPENED), attempt 1
could not be resumed in place; attempt 2 is a fresh attempt. That is safe precisely because durable
spend is summed across **every** attempt state: attempt 2 opened seeing prior spend 156 calls /
364.519 s, carried L1 and L2 at zero cost, did not spawn the `last` session at all, and flew only
L3's 78 contacts — landing the sweep at exactly 234 calls / 546.778 s.

## 4. Contacts and spend

| Column | Attempt 1 (aborted) | Attempt 2 (completed) | Sweep total | Planned | Registered | Headroom |
|---|---|---|---|---|---|---|
| Embedding contacts | 156 | 78 | **234** | 234 | 260 | 26 |
| Metered speech-audio seconds | 364.519 | 182.259 | **546.778** | 600 | 600 | 53.222 |
| GPU hours | 0.031 *(measured, not durably recorded — see below)* | 0.006 | **≈0.038** | 0.3 | 0.3 | ≈0.262 |

By kind: 180 audio + 54 text (60 + 18 per arm × 3). Mean latency: attempt 1 audio 0.080 s / 0.066 s
(L1 / L2), text 0.014 s / 0.012 s; attempt 2 audio 0.115 s, text 0.032 s. Flight wall 113.4 s
(attempt 1) and 23.5 s (attempt 2).

Attempt 1's `gpu_seconds` is durably recorded as **0.0**, which understates reality: the launcher
accumulated session residency only after the teardown call, and that call raised. The honest figure
is its own receipt's `wall_seconds` of 113.36 s of server residency. Attempt 2 recorded 22.577
GPU-seconds durably. Both are far inside the 0.3 GPU-h ceiling, and the shortfall is an accounting
gap in the aborted attempt's receipt, not unmetered spend — the CALL and AUDIO figures, which are the
budgeted quantities, were persisted before every request left the process.

Prior durable spend on this run id was 0 before attempt 1, exactly as the registration's feasibility
statement declared. The gate (`FrozenCoreGate.assert_model_touch_allowed(plan)`) ran in full before
each spawn, then `assert_no_conflicting_generation_server`, then the durable attempt opened
atomically; every contact's spend was persisted **before** the request left the process and checked
against the plan ceiling including sibling attempts. A text contact meters zero speech audio and was
charged the documented `1e-9` s sentinel (54 of them sum to 5.4e-8 s) only because `record_usage`
refuses a non-positive figure.

## 5. Vector manifests (structural only)

Written to `$SPEECHRL_DATA_DIR/derived/embeddings/SAEA-PROBE-pemb3l-234/<arm>/`, one per arm, by the
parent `write_embedding_manifest` reused unmodified. Derived artifacts: they stay on the data root and
never enter Git. `embedding-manifest-summary.json` here is their STRUCTURAL index (contact id, kind,
relpath, dims, sha256 — no vector component).

| Arm | Schema | Entries | By kind | Dims | `.npy` present | Distinct vector sha256 |
|---|---|---|---|---|---|---|
| `l1-last-bare` | `saea-pemb-embeddings-manifest-v1` | 78 | 60 audio / 18 text | 2048 | 78/78 @ 8,320 B | **78** |
| `l2-last-instruct` | same | 78 | 60 / 18 | 2048 | 78/78 @ 8,320 B | **78** |
| `l3-mean-instruct` | same | 78 | 60 / 18 | 2048 | 78/78 @ 8,320 B | **78** |

Within every arm all 78 vectors are byte-distinct, so nothing collapsed to a degenerate constant.
That byte-identity count is the only "did the model do something" check performed here.

## 6. Cross-arm byte identity — an operational finding the read must account for

Same class of check as the per-arm distinctness above: **content hashes only**, keyed on the same
`contact_id`. No vector value is read, no two vectors are compared numerically, no accuracy exists.

| Pair | Audio vectors byte-identical | Text vectors byte-identical |
|---|---|---|
| `l1-last-bare` vs `l2-last-instruct` | 0 / 60 | 0 / 18 |
| `l1-last-bare` vs `l3-mean-instruct` | 0 / 60 | 0 / 18 |
| **`l2-last-instruct` vs `l3-mean-instruct`** | **60 / 60** | 0 / 18 |

L2 and L3 differ ONLY in pooling mode. Their 18 text vectors differ under that change, but **all 60
audio vectors are byte-for-byte identical** — so on the audio side the `--pooling` flag produced no
difference whatsoever, even though the servers self-reported distinct `pooling_type` values (`[3]`
last, `[1]` mean) and the flag is accepted by this build.

The adjacent operational fact, from the servers' own logs: `init: embeddings required but some input
tokens were not marked as outputs -> overriding` fires **exactly once per AUDIO contact and never for
a text contact** — 120 lines in the two-arm `last` session, 60 in the one-arm `mean` session. The
consumed P-EMB-1 flight logged the same warning at the same 60-per-60-audio-contacts rate.

Stated without interpretation: for audio inputs this build overrides the output-token marking, and
under that override `last` and `mean` pooling yield identical vectors, while the instruct prefix does
change every vector on both sides. **The registered L2-vs-L3 contrast is therefore a text-side-only
pooling contrast on this build.** Whether that changes any clause is the read's call, not this
receipt's; it is flagged here because it bears directly on how the L3 arm may be described.

## 7. Hygiene evidence

- **Suite**: 3059 passed, 9 skipped at the flight commit on a quiet machine (66.8 s,
  `preflight-pytest.log`). An earlier full-suite pass under heavy load showed 3058 passed / 1 failed —
  `test_session.py::TestStartSessionSpawn::test_spawn_writes_a_session_receipt_bound_to_the_real_process`,
  whose fake binary is a shell script whose entire lifetime is `sleep 5`, so a loaded machine can
  delay the readiness check past the child's exit. `preflight-pytest-rerun.log` shows 5/5 isolated
  passes plus the whole class, the whole module and the P-EMB-3L machinery green; the clean 3059 was
  then reproduced end-to-end. Load-induced timing flake, unrelated to any flown path.
- **Runtime pins**: llama.cpp build commit `5d9dfcb58ea860295da8fc93c7b5bed9e2c71151`; binary and both
  GGUF files match their receipt pins on byte count and sha256 (`gguf-verify.log`).
- **Feature cache**: `/home/chao/feat-cache/slurp-q4km` held 63 entries before and 63 after — the
  embedding-mode encoder pass was served from the SAME cache the consumed SLURP flights warmed over
  these same 60 clips. Legacy `q4km` (34,350 entries) and `audio2tool-q4km` (490) untouched.
- **Coexistence**: the PRECOMP wave-2 generation server (port 8080, meeting repo) was observed to
  yield before takeoff; nothing answered on 8080 before either spawn. No server is resident
  afterwards and the GPU is back to 114 MiB.
- **D3 gate**: `PYTHONDONTWRITEBYTECODE=1` throughout; zero `__pycache__`/`*.pyc` under the frozen
  scoring package before and after.
- **Ledger**: the exposure row matched exactly once, `consumed=no` at both takeoffs, cells
  260 / 600 / 0.3 agreeing verbatim with the launcher's transcribed ceilings.

## 8. Files

| File | What it is |
|---|---|
| `README.md` | this receipt |
| `launcher/` | every file that produced the run (env, identity, pre-flight, launcher, post-flight, archive, ledger helper, session wrappers, marker/yield/diagnostic probes) |
| `session-precheck.log` | session-start environment probe (git, GPU, caches, orphans, disk) |
| `preflight-pytest.log` | the full suite at the flight commit |
| `preflight-pytest-rerun.log` | isolation evidence for the load-induced suite flake |
| `marker-probe.log` | model-free binary evidence for the `LLAMA_MEDIA_MARKER` pin and the accepted `--pooling` values |
| `preflight.log` | pre-flight (binding sha256, split identity, counts, audio profile, ledger, budgets, per-session argv, marker pin, coexistence, feasibility) |
| `gguf-verify.log` | binary + per-file GGUF sha256 against the runtime receipt |
| `flight.log` | operational flight log for BOTH attempts (contact index, kind, contact id, latency, dims only) |
| `abort-partial-state.log` | what survived attempt 1, and the arithmetic showing attempt 2 fits the ceilings |
| `abort-repair-proof.log` | the zombie bug reproduced and the repaired predicate verified |
| `cross-arm-identity.log` | section 6's byte-identity accounting and the server-log warning counts |
| `postflight.log` | post-flight structural verification |
| `flight-receipt.json` | attempt 2's receipt (identity, cost, per-arm and per-session records, gate diagnostics) |
| `attempt1-aborted-*.json` | attempt 1's receipt, contacts, plan and durable attempt state |
| `execution-plan.json` | the validated `ExecutionPlan` |
| `config-values.json` | the hashed config values bundle (both sessions' argv inside one hash) |
| `session-receipt-last.json`, `session-receipt-mean.json` | the two embedding-mode llama-server session receipts |
| `session-last.server.log`, `session-mean.server.log` | each server's own log (recipe as-built, pooling_type, override warning) |
| `attempt-state.json` | attempt 2's durable attempt file (state machine + persisted actual spend) |
| `contacts.json`, `attempt1-aborted-contacts.json` | per-contact records from the client itself (id, kind, timestamp, latency, dims) |
| `embedding-manifest-summary.json` | STRUCTURAL index of all three vector manifests. The vectors themselves stay on the data root, never in Git |
| `MANIFEST.sha256` | sha256 over every file above |
