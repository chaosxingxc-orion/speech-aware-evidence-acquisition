# P-SLU Stage-2 flight (2026-08-18) — FLOWN, COMPLETED (183/183, zero failures)

Flight-execution receipt for the registered probe
`docs/readiness/2026-08-18-pslu-s2-preregistration-REGISTERED.md`, exposure row
**`SAEA-PROBE-pslu-s2-183`** (`bounded-discovery-probe`). Structural replica of the parent P-SLU
attempt-4 flight (`docs/checks/speech-aware-evidence-acquisition/2026-08-17-pslu-flight/`,
commit `e7d8790`, attempt `attempt-20260818T010218Z-4c97cb`): same server binary (hash-verified),
same GGUF pins, same decode config, same frozen 60-sample devel manifest.

**The probe flew end to end in one pass.** All 183 registered requests were flown against the
frozen core with **zero failures, zero retries, zero resumes and zero replays**; `outputs.jsonl`
carries 183 rows for the separately-registered one-shot read mission. This agent read no result:
no response text, no metric, no phase-1 chosen-label value was opened at any point. Row accounting
touched only the `arm` / `sample_id` / `silence_swapped` keys plus the closed-set mapping
machinery's own `fallback` / `outcome` flags (structural counters).

The exposure row stays **`consumed = no`** — it flips only in the registered read session.

## Identity

| field | value |
|---|---|
| run id | `SAEA-PROBE-pslu-s2-183` |
| attempt id | `attempt-20260818T200339Z-80119a` |
| config hash | `9cab7b17f77f03c729e76a21725a31def90113a00e20fa53d733ab7e6e24bd00` |
| protocol hash | `ee29c40569b1fdea131bcf45a996837b2d7fa221fed54a8381339ac797bd1001` |
| split identity hash | `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` |
| trace manifest hash | `103355d2e5ae90f92d1388705af06e6fa629522aacb8249af62e4e70b21cee12` |
| umbrella lock sha256 (at close) | `b588f3641ae1d1774fb7652c8978acf25eda7dcbc45a34a898d5471bce5b2e42` |
| study commit during flight | `852e041` (tree clean before, during and after) |
| status | `COMPLETED`, `error: None` |

The split identity hash is the parent flight's own value verbatim (same frozen 60-sample
manifest, never a fresh draw), and it agrees across the flight receipt, the `ExecutionPlan`,
`configs/probes/g0-binding/pslu-sample-devel-n60.json` and the exposure-ledger cell. The plan
validates as `bounded-discovery-probe` / `discovery` with the registered ceilings 220 / 2000 / 0.5.

## Pre-flight: CLEAN (all gates; logs archived here)

- **Full pytest suite** (`preflight-pytest.log`): **2491 passed, 9 skipped** in 64.4 s at
  `852e041` — includes the coordinator-reviewed Stage-2 machinery and read-suite unit tests.
- **Model-free preflight** (`preflight.log`, `launcher/preflight.py`): 8,690 devel samples
  loaded, the frozen 60 selected, **60/60 flac present**, **182.26 s** audio (mean 3.04 s),
  **89 gold slots**, **18** distinct gold scenarios, roster table legal (18/55/100/18),
  **18 canonical closed-set labels** for phase 1, all 3 silence-swap ids inside the frozen 60,
  exposure row present exactly once with `consumed = no` and budgets 220 / 2000 / 0.5,
  `ExecutionPlan` validating, and the registered call arithmetic 60+60+60+3 = 183 ≤ 220.
- **F1 filler binding check — fail-closed PASS** (`preflight.log`): the 300-word committed
  lexicon loads under its own legality checks (`slurp_derived: false` machine-verified), the
  seeded 100-entry roster generates deterministically (seed 20260807), and
  `check_f1_filler_binding` proves **zero overlap** against the 55 ontology type names, every
  ontology value, and the 89 gold slot values of the frozen 60. The same check also runs in the
  committed unit suite; this is the flight-time execution of it.
- **D1 media identity** (`d1-probe.log`): `verify_media_identity('slurp')` **PASS** on the
  governed `datasets/slurp/...` path. Note: a first probe run replayed the parent launcher's
  literal `repos/slurp/scripts/audio/...` path and was REFUSED with "does not exist as a regular
  file" — that pre-lock-fix duplicate location no longer exists on disk (umbrella `344dfdc`
  moved the carrier root to `datasets/slurp`), so the probe input was updated to the governed
  path; the refusal was file-existence, not a D1-closure gap.
- **Runtime pins** (`env-probe-before.log`): llama.cpp build commit
  `5d9dfcb58ea860295da8fc93c7b5bed9e2c71151`, binary sha256
  `097c96ec5a3f576f378d4d5e103928bf070647fdcc1f015eacb839503e121c68` — equal to the parent
  attempt-4 pin — and **both GGUF files hash-verified** against
  `docs/receipts/runtime-q4km-featcache.json` (`0751c279…066d` Q4_K_M, `f0dfe825…2883` mmproj
  bf16), byte counts matching. GGUF VERIFICATION: PASS.
- **Hygiene** (`env-probe-before.log`): tree clean at `852e041`; `PYTHONDONTWRITEBYTECODE=1`
  with **0** `*.pyc` / **0** `__pycache__` under `src/`; GPU idle P8 / 180 MHz / 0x0 throttle
  reasons; campaign cache `/home/chao/feat-cache/slurp-q4km` at 63 entries (warm from the
  parent flight); legacy 26 GB `q4km` cache untouched; no orphan `llama-server`; no prior
  attempt dirs for this run id.

## Flight: 183/183, zero failures

Timeline (UTC, `flight.log`):

| phase | window | duration | note |
|---|---|---|---|
| devel split hash pass | 19:49:46 → 20:03:39 | 833 s | model-free (cold /mnt/e IO) |
| server spawn + model load | 20:03:39 → 20:04:00 | 21 s | |
| payload binding media hashing, slice build | 20:04:00 → 20:19:38 | 938 s | server up but idle; 3 silence-swap `.wav` written |
| **flight loop** — 60 × F1, then 60 × (A1r-phase1 → A1r) + 3 swaps | 20:19:38 → 20:22:55 | 197 s | fully featcache-served |
| close, outputs, receipt | 20:22:55 | — | exit 0 |

Launcher wall 19:49:36 → 20:22:55 = **33 min 19 s**; the flight loop itself (`wall_seconds`)
**196.67 s = 3.3 min**; throughput ≈ 0.93 requests/second, mean request latency 0.78 s.

Row accounting, read structurally from `outputs.jsonl` (`arm-accounting.log`, script
`launcher/arm_counts.sh` — `response_text`, `messages`, `metrics`, `consumption`,
`predicted_raw` and `canonical_label` were never touched):

| arm | rows | distinct samples | silence-swapped |
|---|---|---|---|
| F1 | 60 | 60 | 0 |
| A1r-phase1 | 60 | 60 | 0 |
| A1r | **63** | 60 | **3** |
| **total** | **183** | | **3** |

Zero duplicate `(arm, sample_id, silence_swapped)` keys. This is exactly the registered design:
F1 ×60, the two-phase A1'r ×60 (120 calls), plus the 3 seeded silence-swap controls on A1'r's
own phase-2 request.

**A1'r phase-1 closed-set mapping (structural machinery counters, not content):**
**non-fallback 60/60** — `fallback=False` on every call, mapping outcome `exact` on all 60,
**zero A2-fallbacks**. The parent's A1' fell back 60/60 because free-form phase-1 predictions
never matched a canonical key; as flown, the closed-set phase-1 + deterministic mapper resolved a
canonical label on every call, so the label-space repair operated at the machinery level. (Whether
self-scoping *helps* is the read mission's question; nothing here interprets any content.)

Requests: **flown 183, replayed 0, failures 0, resumes 0**. `request_failures: []`. No server
wedge, no restart, no `--attempt-id` resume was needed. `responses.jsonl` holds 183 lines and
`outputs.jsonl` 183 rows.

## Feature cache: warm end to end — zero growth, zero encode lines

| moment | campaign cache entries | size | dir mtime |
|---|---|---|---|
| before launch | **63** | 23 MB | 2026-08-17 21:08:20 |
| after close | **63** | 23 MB | 2026-08-17 21:08:20 (unmoved) |

The cache never grew and its directory mtime never moved, and the server log carries **0** lines
matching any encode pattern across all 183 requests (`postflight.log`) — the entire flight was
served from the parent flight's warm entries. Even the 3 newly-written silence-swap slice `.wav`s
hit the cache: they are byte-content-identical silent audio of the same durations as the parent's
registered slices, so their cache keys resolve to the parent's existing 3 slice entries. That
zero-delta + zero-encode-line shape is the hit evidence (the patch logs nothing on hits). The
legacy 26 GB `/home/chao/feat-cache/q4km` was never opened: still 34,350 entries, dir mtime
unchanged at `2026-08-16 14:09:12`.

## GPU note

No clock intervention was applied and none was warranted: the 183-request loop ran at ≈ 0.93
requests/second and finished in 197 s (the known failure mode is a *slowdown*, which did not
occur; per the s2c precedent the clock reading alone is not the defect). GPU was idle P8 /
180 MHz with `0x0` throttle reasons at pre-flight.

## Cost

| quantity | registered ceiling | consumed this attempt | share |
|---|---|---|---|
| core calls | ≤ 220 | **183** | 83.2 % |
| speech audio seconds | ≤ 2000 | **554.46** | 27.7 % |
| GPU hours | ≤ 0.5 | **≈ 0.317** (server resident 1,141 s); decode latency total 142.62 s = 0.040 h | ≤ 63.4 % |

Prompt tokens 79,673; completion tokens 9,765; tool calls 0. The GPU-hour figure is dominated by
the 938 s payload-binding hash pass that ran with the model loaded but idle (cold /mnt/e IO this
session; the parent's warm-cache binding took 78 s) — decode occupancy itself was 0.040 h. The
metered audio matches the registered formula: 182.26 s × 3 sends per sample + 7.68 s of
silence-swap slices = 554.46 s. No ceiling was approached by the fail-closed meter.

## State left behind

`$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-s2-183/attempt-20260818T200339Z-80119a/` (outside Git):

| artifact | size | note |
|---|---|---|
| `outputs.jsonl` | 1.32 MB, 183 rows | **the read mission's input**; written, never read here; A1r-phase1 rows embed `closed_set_mapping` |
| `responses.jsonl` | 80 KB, 183 lines | resume cache |
| `SAEA-PROBE-pslu-s2-183.trace.jsonl` | 530 KB | raw ConsumptionTrace (never committed) |
| `SAEA-PROBE-pslu-s2-183.trace-manifest.json` | 52 KB, 549 records | closed, hash `103355d2…` |
| `flight-receipt.json` | 44 KB | status `COMPLETED`; longest string 108 chars — a receipt, not a trace |
| `…plan.json`, `…config-values.json`, `…session-receipt.json`, `…server.log` | | copies of the first four archived here |

Also three silence-swap slice `.wav` files under
`$SPEECHRL_DATA_DIR/derived/obs-slices/SAEA-PROBE-pslu-s2-183/` (derived data, outside Git).

`client.close()` ran cleanly and produced the close receipt; no orphaned `llama-server` after
exit; the study working tree stayed clean at `852e041` for the whole attempt and the launcher ran
from scratchpad (`launcher/` here is the byte-verbatim archive of everything that ran).

## What the read mission needs

- run id `SAEA-PROBE-pslu-s2-183`, attempt id **`attempt-20260818T200339Z-80119a`**;
- input `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-s2-183/attempt-20260818T200339Z-80119a/outputs.jsonl`
  (183 rows; `closed_set_mapping` embedded on each A1r-phase1 row);
- identity to check against the registration: config `9cab7b17…`, protocol `ee29c405…`, split
  `fc9de436…`, trace manifest `103355d2…`;
- the exposure row is still `consumed = no`; the single registered read session flips it.

Nothing about the flight is known to compromise the read: both arms plus the swaps flew over the
identical frozen 60 in one pass, no request failed, no response was replayed from any earlier
attempt (this is the first and only attempt for this run id), and no result was observed by
flight operations.
