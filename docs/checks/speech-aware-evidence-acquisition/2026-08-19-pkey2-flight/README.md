# P-KEY successor flight (2026-08-19) — FLOWN, COMPLETED (338/338, zero failures)

Flight-execution receipt for the registered probe
`docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md` (§1–§7 design, §7 and §8
amendments), exposure row **`SAEA-PROBE-pkey2-338`** (`bounded-discovery-probe`). This is the
**successor run** created by §8 after `SAEA-PROBE-pkey-303` was closed NOT-CONSUMED: attempt-1's
183 durable calls are charged to the predecessor row forever, so no compliant attempt could ever
fly under it. The design is unchanged; only run identity and accounting are fresh.

**The probe flew end to end in one session.** All 338 registered requests — the six passes
T0 ×60, AUD-NOSUP ×60, AUD-SUP ×60 (+3 seeded silence-swaps), TXT-NOSUP ×60, TXT-SUP ×60 and the
2026-08-19 amendment's TXT-NOSUP duplicate sub-block ×35 — were flown against the frozen core with
**zero failures, zero retries, zero resumes and zero replays**; `outputs.jsonl` carries 338 rows
for the separately-registered one-shot read mission. This agent read no result: no response text,
no metric, no transcript, no consumption value was opened at any point. Row accounting touched only
the `arm` / `sample_id` / `silence_swapped` / `txt_duplicate` keys and the *presence* of
`transcript_sha256_used` (structural flags). Request-level log lines carry a character count only.

The exposure row stays **`consumed = no`** — it flips only in the registered read session.

## Identity

| field | value |
|---|---|
| run id | `SAEA-PROBE-pkey2-338` |
| attempt id | `attempt-20260819T111032Z-3109e8` |
| config hash | `349b5fa9dfb49541e7ff20a0968a3fd68b9687c1987cbead9cc271599857cdd1` |
| protocol hash | `c4ca737b1326bb089217dfaf18347c2aa6164944643c00ac515b3d0a30a6b307` |
| split identity hash | `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` |
| trace manifest hash | `574f9e9a6afe70901ae292263145cbb8510c553f40d183c54edba628ca2d60a2` |
| umbrella lock sha256 (at close) | `ad71f96732a2b69fb741b4fed4fe60fb1978dc23eb55522ce3943702f0801d1e` |
| study commit during flight | `4e8b948` (tree clean before, during and after) |
| status | `COMPLETED`, `error: None` |

The split identity hash is the consumed P-SLU probes' own value verbatim (the SAME frozen
60-sample devel manifest, seed 20260807, never a fresh draw), and it agrees across the flight
receipt, the `ExecutionPlan`, the committed sample-manifest binding, the machinery's
`EXPECTED_SPLIT_IDENTITY_HASH` and the exposure-ledger cell. The plan validates as
`bounded-discovery-probe` / `discovery` against the fresh ceilings 360 / 2500 / 0.6.

Run identity is bound in exactly one place (`launcher/flight_identity.py`, `RUN_ID`); the
committed flight config binds none. The decode config — `decoding_params`, `server_args`,
`server_env` — is byte-identical to the consumed P-SLU Stage-2 flight's, which is what the
registration requires ("decode config identical to the consumed P-SLU flights"). The
`config_hash`/`protocol_hash` differ from the predecessor pre-flight's by the two run-identity
strings only (`RUN_ID` and the `launcher` provenance value); nothing pins either hash.

## Pre-flight: CLEAN (all gates; logs archived here)

- **Full pytest suite** (`preflight-pytest.log`): **2682 passed, 9 skipped** in 96.5 s at
  `4e8b948` — includes the real-client text-path repair and the duplicate sub-block machinery
  landed at `01583dc`.
- **Model-free preflight** (`preflight.log`, `launcher/preflight.py`): 8,690 devel samples loaded,
  the frozen 60 selected, **60/60 flac present**, **182.26 s** audio (mean 3.04 s), rosters legal
  (18 scenarios / 55 global types / 100 full-roster entries / 18 derangement keys), A3 packet 100
  items, config/code parity PASS on `t0_instruction` + `txt_template` + both sha256 companions,
  all 3 silence-swap ids and all 35 txt-duplicate ids inside the frozen 60 and both draws
  **re-derived deterministically from seed 20260807** (salt `txt-duplicate` for the sub-block),
  exposure row present exactly once with `consumed = no` and budgets 360 / 2500 / 0.6,
  `ExecutionPlan` validating, and the registered call arithmetic
  60+60+60+60+60+3+35 = **338 ≤ 338 plan ceiling ≤ 360 registered**.
- **Run-total feasibility (the check that refused attempt-2 under the predecessor row)**: prior
  durable spend on `SAEA-PROBE-pkey2-338` = **0 calls / 0.00 audio-seconds**; a fresh full attempt
  fits with headroom. This is the fail-closed gate §8 was written around, and it passed only
  because the run is a successor with its own accounting.
- **D1 media identity** (`d1-probe.log`): `verify_media_identity('slurp')` **PASS** on the governed
  `datasets/slurp/...` path.
- **Runtime pins** (`gguf-verify.log`): llama.cpp build commit
  `5d9dfcb58ea860295da8fc93c7b5bed9e2c71151`, binary sha256
  `097c96ec5a3f576f378d4d5e103928bf070647fdcc1f015eacb839503e121c68` — equal to the P-SLU
  Stage-2 pin — and **both GGUF files hash-verified** against
  `docs/receipts/runtime-q4km-featcache.json` (`0751c279…066d` Q4_K_M, `f0dfe825…2883` mmproj
  bf16), byte counts matching. BINARY+GGUF VERIFICATION: PASS.
- **Import / parity check** (`import-check.log`): every launcher module compiles, machinery arms
  `('T0','AUD-NOSUP','AUD-SUP','TXT-NOSUP','TXT-SUP')`, machinery split-identity pin equal to the
  manifest's, config/code parity guard PASS (model-free).
- **Hygiene** (`hygiene.log`): tree clean at `4e8b948`; `PYTHONDONTWRITEBYTECODE=1` with **0**
  `*.pyc` / **0** `__pycache__` under `src/`; GPU idle P8 / 180 MHz / `0x0` throttle reasons;
  campaign cache `/home/chao/feat-cache/slurp-q4km` at 63 entries (warm from the P-SLU flights);
  legacy 26 GB `q4km` cache untouched; no orphan `llama-server`; no prior attempt dir for this run
  id.

## Flight: 338/338, zero failures

Timeline (UTC, `flight.log`):

| phase | window | duration | note |
|---|---|---|---|
| devel split hash pass | 11:08:42 → 11:10:32 | 110 s | model-free |
| server spawn + model load | 11:10:32 → 11:10:55 | 23 s | |
| payload binding, slice build | 11:10:55 → 11:14:19 | 204 s | server up but idle; 3 silence-swap `.wav` written |
| pass 0 — T0 ×60 | 11:14:20 → 11:15:18 | 58 s | |
| pass 1 — AUD-NOSUP ×60 | 11:15:22 → 11:19:10 | 228 s | |
| pass 2 — AUD-SUP ×60 + 3 swaps | 11:19:14 → 11:24:50 | 336 s | |
| pass 3 — TXT-NOSUP ×60 | 11:24:53 → 11:29:07 | 254 s | audio-free |
| pass 4 — TXT-SUP ×60 | 11:29:11 → 11:34:18 | 307 s | audio-free |
| pass 5 — TXT-NOSUP-DUP ×35 | 11:34:22 → 11:36:50 | 148 s | audio-free |
| close, outputs, receipt | 11:36:50 | — | exit 0 |

Launcher wall 11:08:40 → 11:36:50 = **28 min 10 s**; the flight loop itself (`wall_seconds`)
**1351.25 s = 22.5 min**; throughput ≈ 0.25 requests/second, mean request latency 3.86 s.

Row accounting, read structurally from `outputs.jsonl` (`arm-accounting.log` and
`txt-duplicate-accounting.log`, scripts `launcher/arm_counts.sh` and `launcher/txt_dup_counts.sh` —
`response_text`, `messages`, `metrics`, `consumption` and the transcript registry's contents were
never touched):

| pass | arm | rows | distinct samples | swapped | txt_duplicate | `transcript_sha256_used` |
|---|---|---|---|---|---|---|
| 0 | T0 | 60 | 60 | 0 | 0 | absent 60/60 |
| 1 | AUD-NOSUP | 60 | 60 | 0 | 0 | absent 60/60 |
| 2 | AUD-SUP | **63** | 60 | **3** | 0 | absent 63/63 |
| 3 | TXT-NOSUP | 60 | 60 | 0 | 0 | **present 60/60** |
| 4 | TXT-SUP | 60 | 60 | 0 | 0 | **present 60/60** |
| 5 | TXT-NOSUP (duplicate sub-block) | **35** | 35 | 0 | **35** | **present 35/35** |
| | **total** | **338** | | **3** | **35** | |

Zero duplicate `(arm, sample_id, silence_swapped, txt_duplicate)` keys. The 35 rows that share an
`(arm, sample_id)` pair with a pass-3 row are exactly the amendment's registered duplicate
sub-block, flagged `txt_duplicate=True` and kept in its own bucket by both the flight validator and
the read suite — never merged into the primary per-sample aggregate. `transcript-registry.json`
holds **60 entries**, one per frozen sample, hash-recorded at pass 0.

**Structural validator: PASS.** `rails.probes.pkey_flight.validate_pkey_flight_summary` runs
fail-closed at the end of `run_pkey_flight`, and the flight reaching `COMPLETED` is that check
passing: exactly one row per arm per frozen sample id, no duplicate sample rows, exactly one
silence-swap row per registered swap id (all on AUD-SUP), exactly one txt-duplicate row per
registered duplicate id (all on TXT-NOSUP, each **byte-identical** to that same sample's own pass-3
row — the amendment's own byte-identity bar), every TXT-* row audio-free, and every TXT-* row's own
rendered transcript text sha256-matching this same summary's T0 row for the same sample. The
launcher additionally shows the modality split structurally in `flight.log`: **183 requests carry a
media path, 155 carry `media=<none>`** (60+60+60+3 audio vs 60+60+35 text) — the transport
invariant the predecessor aborted on is satisfied in both directions.

Requests: **flown 338, replayed 0, failures 0, resumes 0**. `request_failures: []`. No server
wedge, no restart, no `--attempt-id` resume was needed. `responses.jsonl` holds 338 lines and
`outputs.jsonl` 338 rows.

## Feature cache: warm end to end — zero growth, zero encode lines

| moment | campaign cache entries | size | dir mtime |
|---|---|---|---|
| before launch | **63** | 23 MB | 2026-08-17 21:08:20 |
| after close | **63** | 23 MB | 2026-08-17 21:08:20 (unmoved) |

The cache never grew and its directory mtime never moved, and the 10.2 MB server log carries **0**
lines matching any encode pattern across all 338 requests (`postflight.log`) — the entire flight
was served from the P-SLU flights' warm entries. The 3 newly-written silence-swap slice `.wav`s hit
the cache too: byte-content-identical silence of the same durations (1.98 s / 3.14 s / 2.56 s =
7.68 s) as the registered slices, so their cache keys resolve to existing entries. That
zero-delta + zero-encode-line shape is the hit evidence (the patch logs nothing on hits). The
legacy 26 GB `/home/chao/feat-cache/q4km` was never opened: still 34,350 entries, dir mtime
unchanged at `2026-08-16 14:09:12`.

## GPU note

No clock intervention was applied and none was warranted: GPU was idle P8 / 180 MHz with `0x0`
throttle reasons at pre-flight, and the loop sustained ≈ 0.25 requests/second with no slowdown
signature across 22.5 minutes (the known failure mode is a *slowdown*; per the s2c precedent the
clock reading alone is not the defect). The per-request latencies rise from the ≈0.8 s T0 pass to
≈4 s on the supply arms because those prompts carry the 100-entry roster, not because of any
throttle.

## Cost

| quantity | registered ceiling | consumed this attempt | share |
|---|---|---|---|
| core calls | ≤ 360 | **338** | 93.9 % |
| speech audio seconds | ≤ 2500 | **1025.27** (metered) | 41.0 % |
| GPU hours | ≤ 0.6 | **≈ 0.438** (server resident 1,578 s); decode latency total 1,303.61 s = 0.362 h | ≤ 73.0 % |

Prompt tokens 121,916; completion tokens 18,425; tool calls 0. The metered audio matches the
pre-flight arithmetic: 182.26 s × 3 audio passes + 7.68 s of silence-swap slices = 554.46 s of
audio actually decoded, plus the fail-closed meter's TXT bookkeeping (182.26 + 182.26 + 106.30 for
the three audio-free passes, which send no audio) = 1025.27 s. No ceiling was approached.

Predecessor accounting is untouched: `SAEA-PROBE-pkey-303` keeps its attempt-1 dead spend
(183 calls / 554.46 audio-seconds, never read) and its `consumed = no` closure note.

## State left behind

`$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338/attempt-20260819T111032Z-3109e8/` (outside Git):

| artifact | size | note |
|---|---|---|
| `outputs.jsonl` | 2.13 MB, 338 rows | **the read mission's input**; written, never read here |
| `transcript-registry.json` | 14.7 KB, 60 entries | T0 transcripts + hashes, pass-0 recorded; never opened here |
| `responses.jsonl` | 142 KB, 338 lines | resume cache |
| `SAEA-PROBE-pkey2-338.trace.jsonl` | 927 KB | raw ConsumptionTrace (never committed) |
| `SAEA-PROBE-pkey2-338.trace-manifest.json` | 93.7 KB, 1,014 records | hash `574f9e9a…` |
| `SAEA-PROBE-pkey2-338.server.log` | 10.2 MB | zero encode lines |
| `flight-receipt.json` | 77 KB | status `COMPLETED`; longest string 106 chars — a receipt, not a trace |
| `…plan.json`, `…config-values.json`, `…session-receipt.json` | | copies archived here |

Also three silence-swap slice `.wav` files under
`$SPEECHRL_DATA_DIR/derived/obs-slices/SAEA-PROBE-pkey2-338/` (derived data, outside Git).

`client.close()` ran cleanly and produced the close receipt; no orphaned `llama-server` after exit;
the study working tree stayed clean at `4e8b948` for the whole attempt and the launcher ran from
scratchpad (`launcher/` here is the byte-verbatim archive of everything that ran, including the
landing-side structural scripts).

## What the read mission needs

- run id `SAEA-PROBE-pkey2-338`, attempt id **`attempt-20260819T111032Z-3109e8`**;
- input `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pkey2-338/attempt-20260819T111032Z-3109e8/outputs.jsonl`
  (338 rows) plus that directory's `transcript-registry.json` (60 entries);
- identity to check against the registration: config `349b5fa9…`, protocol `c4ca737b…`, split
  `fc9de436…`, trace manifest `574f9e9a…`;
- the §7 amendment's read obligations are unchanged and unmet by this flight: the paired cluster
  bootstrap with the published σ̂(I) and 90 % CI, the CI-gated KEY-ONLY clause, the mandatory
  pre-read reachability statement, and the n ≤ 4 NEAR-MISS caveat. The 35 duplicate rows exist to
  give the TXT axis its own measured duplicate floor for that bootstrap;
- the exposure row is still `consumed = no`; the single registered read session flips it.

Nothing about the flight is known to compromise the read: all six passes flew over the identical
frozen 60 in one session (the in-session comparability the factorial is designed around), no
request failed, no response was replayed from any earlier attempt (this is the first and only
attempt for this run id, and attempt-1 of the closed predecessor run is never read), and no result
was observed by flight operations.
