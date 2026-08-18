# P-SLU flight attempt 4 (2026-08-18) — FLOWN, COMPLETED (363/363, zero failures)

This file is **appended** to the 2026-08-17 attempt-1 / attempt-2 / attempt-3 archive; no earlier
file was modified. It records the fourth and successful flight of the registered probe
`docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md`, exposure row `SAEA-PROBE-pslu-n60`.

**The probe flew end to end.** All 363 registered requests were flown against the frozen core with
**zero failures, zero retries, zero resumes and zero replays**; `outputs.jsonl` carries 363 rows for
the separately-registered one-shot read mission. The flight consumed **363 of 450** calls,
**1,101.24 of 1,500** audio-seconds and roughly **0.12 of 0.5** GPU-hours. This agent read no result:
no response text, no metric, no scenario prediction value was opened at any point.

The exposure row stays **`consumed = no`** — it flips only in the registered read session.

The launcher archived with attempt 1 was run **unmodified** (provenance below).

## Identity

| field | value |
|---|---|
| run id | `SAEA-PROBE-pslu-n60` |
| attempt id | `attempt-20260818T010218Z-4c97cb` |
| config hash | `a72c7a6cadda40a852a766e8eed9b99f0a9d0daf7c7784f9fa01780df9f5ee4d` |
| protocol hash | `5a9d989d9e628f91fd6b49c6eb400b29b9556b80583b14d4dfc8fe0b6de8d72c` |
| split identity hash | `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` |
| trace manifest hash | `bc25cb53e597e404520168b6dd2bedfd830b3f2bc9b87bd16a29dff108059a5f` |
| umbrella lock sha256 (at close) | `38bcaf2ab6d39d6d954e54e691a55e8245354462b92d4d8a7921b1065f9101e3` |
| study commit during flight | `7d65909` (tree clean before, during and after) |
| status | `COMPLETED`, `error: None` |

Config and protocol hashes are byte-identical to attempts 2 and 3. The identity that flew is the
registered one: the umbrella lock repair that unblocked this attempt changed **no** part of the run
identity, and the plan validates as `bounded-discovery-probe` / `discovery` with the registered
ceilings 450 / 1500 / 0.5.

## The attempt-3 blocker: CLEARED at the governance layer, verified before launch

Attempt 3 was refused inside `core/model/paths.py::_resolve_confined` because the SLURP lock entry
carried two disagreeing path authorities: `local_subdir` (hence `asset_dir`, hence every rails
`carrier_root`) pointed at `repos/slurp/scripts/audio`, while every loader-emitted `media_relpath`
lived under `datasets/slurp`.

That was resolved **where attempt 3 said it had to be** — once, in the lock, for both consumers.
Umbrella commit `344dfdc` (`fix(lock): slurp carrier root is the governed copy datasets/slurp`)
sets the entry's `local_subdir` to `datasets/slurp`, making the canonical carrier-root resolver
agree with the tree the annotation receipt reconciled. It is a one-line change to
`docs/datasets.lock.json`; the `repos/slurp` reference-repo entry is untouched, and physical
reclamation of the duplicate remains a pending owner decision.

Verified read-only before launch (`attempt4-confinement-sanity.log`, source
`attempt4-confinement-sanity.py`), resolving `carrier_root` exactly the way `core/driver/run.py`
does:

```
=== lock entry (slurp) ===
  local_subdir:    datasets/slurp
  governed_copy:   datasets/slurp/metadata

=== carrier_root, resolved the way core/driver/run.py does ===
  asset_dir(...):   /mnt/e/.../speechrl-data/datasets/slurp
  == $SPEECHRL_DATA_DIR/datasets/slurp ? True

=== request-1 sample ===
  sample_id:       slurp:devel:000115:audio-1495375974
  media_relpath:   datasets/slurp/slurp_real/audio-1495375974.flac
  INSIDE carrier_root: True

=== all 60 media_relpaths confined? ===
  outside carrier_root: 0/60

CONFINEMENT SANITY: PASS
```

`audio-1495375974.flac` is the exact file that refused attempt 3. It now resolves inside the
carrier root, as do all 60. `build_payload_binding` — the rail that raised the refusal — constructs
cleanly.

**The pre-flight proves the fix was surgical.** `attempt4-preflight.log` differs from
`attempt3-preflight.log` on **exactly one line**:

```
< carrier_root (asset_dir slurp): .../speechrl-data/repos/slurp/scripts/audio
> carrier_root (asset_dir slurp): .../speechrl-data/datasets/slurp
```

Every other registered fact reproduced bit-for-bit across attempts 2, 3 and 4.

## Pre-flight: CLEAN (all seven gates)

`attempt4-preflight.log` — 8,690 devel samples loaded and 60 selected in the frozen order,
**60/60 flac present**, **182.26 s** total audio (mean 3.04 s), **89 gold slots**, **18** distinct
gold scenarios, roster table legal (18 scenario rosters / 55 global types / 100 dose-capped entries /
18 derangement keys), all 3 silence-swap ids inside the frozen 60, exposure row present exactly once
with `consumed = no` and budgets 450 / 1500 / 0.5, and the `ExecutionPlan` validating.

Hygiene before launch (`attempt4-env-probe-before.log`, script `attempt4-hygiene.sh`):

| gate | measured |
|---|---|
| study tree | clean at `7d65909`, and clean for the whole flight |
| umbrella lock | at `344dfdc` (the fix) |
| bytecode | `PYTHONDONTWRITEBYTECODE=1`; **0** `*.pyc`, **0** `__pycache__` under `src/` |
| campaign feature cache | `/home/chao/feat-cache/slurp-q4km`, **0 entries** (cold) |
| legacy feature cache | `/home/chao/feat-cache/q4km` 26 GB / 34,350 entries, dir mtime 2026-08-16 — never opened |
| GPU | idle P8 / 180 MHz / 322 MiB / 7.4 W, no throttle reasons active |
| orphan servers | none |
| D1 | `verify_media_identity('slurp'): PASS` |
| model | ext4 copies under `/home/chao/models/…` only, never `/mnt/e` |

## Runtime: healthy and correctly pinned

`attempt4-flight-receipt.json` (`session` block) — identical pins to attempts 2 and 3:

- binary `llama.cpp-featcache/build/bin/llama-server`, sha256
  `097c96ec5a3f576f378d4d5e103928bf070647fdcc1f015eacb839503e121c68`;
- model resolved to the **ext4** copies, both per-file SHA-256 matching
  `docs/receipts/runtime-q4km-featcache.json`: `0751c279…066d` (Q4_K_M) and `f0dfe825…2883`
  (mmproj bf16);
- session `SAEA-PROBE-pslu-n60-attempt-20260818T010218Z-4c97cb`, pid 755, port 8080, startup stdout
  sha256 `8ba3173d…a01`.

## Flight: 363/363, zero failures

Timeline (UTC, `attempt4-flight.log`):

| phase | window | duration | note |
|---|---|---|---|
| devel split hash pass | 01:01:01 → 01:02:18 | 77 s | model-free |
| server spawn + model load | 01:02:18 → 01:02:43 | 25 s | |
| payload binding media hashing, slice build | 01:02:43 → 01:04:01 | 78 s | 3 silence-swap `.wav` written |
| **phase 1** — 60 × A0 | 01:04:01 → 01:04:53 | 52 s | pays the cold encoder cost |
| **phase 2** — 5 arms × 60 + 3 silence-swap | 01:04:53 → 01:10:03 | 310 s | featcache-served |
| close, outputs, receipt | 01:10:03 | — | exit 0 |

Launcher wall 01:00:59 → 01:10:03 = **9 min 4 s**; the flight loop itself (`wall_seconds`)
**361.81 s = 6.0 min**.

Row accounting, read structurally from `outputs.jsonl` (`arm` / `sample_id` /
`silence_swapped` / `phase1_scenario_parsed` keys only — `response_text`, `messages` and `metrics`
were never touched; `attempt4-arm-accounting.log`, script `attempt4-arm-accounting.sh`):

| arm | rows | distinct samples | silence-swapped |
|---|---|---|---|
| A0 | 60 | 60 | 0 |
| A1 | 60 | 60 | 0 |
| A1p | **63** | 60 | **3** |
| A2 | 60 | 60 | 0 |
| A3 | 60 | 60 | 0 |
| A4 | 60 | 60 | 0 |
| **total** | **363** | | **3** |

This is exactly the registered design: six arms over the frozen 60, plus the three seeded
silence-swap controls on A1'. All 60 phase-1 scenario predictions parsed
(`phase1_scenario_parsed = True` × 60), so A1' had a self-supplied scenario for every sample and
never silently degenerated to A0; `predicted-scenarios.json` holds 60 entries (values not opened).

Requests: **flown 363, replayed 0, failures 0, resumes 0**. `request_failures: []`. No server wedge,
no restart, no `--attempt-id` resume was needed. `responses.jsonl` holds 363 lines and
`outputs.jsonl` 363 rows.

## Feature cache: cold-start shape confirmed by growth, not by reading outputs

| moment | campaign cache entries | size |
|---|---|---|
| before launch | 0 | 4 KB (empty dir) |
| mid phase 2 (≈ request 130) | **60** | 22 MB |
| after close | **63** | 23 MB |

The cache reached 60 entries — one per distinct audio file — during phase 1's 60 A0 requests, then
**stopped growing while 303 further requests flew**. The only later additions are the 3 silence-swap
slice `.wav`s. Phase-1 latency averaged ≈ 0.87 s/request paying the encode; phase-2 requests settled
at 0.5–1.3 s with the encoder served from cache. That growth curve is the hit evidence, as required —
the patch logs nothing, so hits are proven by an untouched cache and absent encode cost, never by
reading outputs.

The legacy 26 GB `/home/chao/feat-cache/q4km` was **never opened**: still 34,350 entries with dir
mtime unchanged at `2026-08-16 14:09:12`, re-verified after close.

## GPU note: P4 / 232 MHz observed, benign here

The GPU sat at **P4 / 232 MHz** with 91 % utilisation for the whole request loop — the same reading
that has previously signalled a stuck power-capped clock. **No intervention was applied and none was
warranted**: `clocks_throttle_reasons.active` stayed `0x0` throughout, throughput held at ≈ 1.1
requests/second, and the whole 363-request flight finished in 6 minutes. The known failure mode is a
*slowdown* at that clock; there was none, so `-lgc 1200,2500` was deliberately not used. Recorded
here because the reading alone is not the defect — the slowdown is.

## Cost

| quantity | registered ceiling | consumed this attempt | share of ceiling |
|---|---|---|---|
| core calls | ≤ 450 | **363** | 80.7 % |
| speech audio seconds | ≤ 1500 | **1101.24** | 73.4 % |
| GPU hours | ≤ 0.5 | **≈ 0.122** (server resident 440 s); decode latency total 279.80 s = 0.078 h | ≤ 24.4 % |

Prompt tokens 132,516; completion tokens 22,890; tool calls 0. Attempts 1–3 spent nothing, so these
are also the totals to date for this registration. Headroom remaining under the registration: 87
calls and 398.76 audio-seconds.

## State left behind

`$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/attempt-20260818T010218Z-4c97cb/` (outside Git):

| artifact | size | note |
|---|---|---|
| `outputs.jsonl` | 2.7 MB, 363 rows | **the read mission's input**; written, never read here |
| `predicted-scenarios.json` | 4.6 KB, 60 entries | A1' self-supplied scenarios |
| `responses.jsonl` | 168 KB, 363 lines | resume cache |
| `SAEA-PROBE-pslu-n60.trace.jsonl` | 1.0 MB | raw trace (never committed) |
| `SAEA-PROBE-pslu-n60.trace-manifest.json` | 98 KB, 1,089 records | closed, hash `bc25cb53…` |
| `flight-receipt.json` | 81 KB | status `COMPLETED` |
| `…plan.json`, `…config-values.json`, `…session-receipt.json`, `…server.log` | | |

Also three silence-swap slice `.wav` files under
`$SPEECHRL_DATA_DIR/derived/obs-slices/SAEA-PROBE-pslu-n60/` (derived data, outside Git).

`client.close()` ran cleanly and produced the close receipt. No orphaned `llama-server` after exit.
The study working tree stayed clean for the whole attempt and the launcher ran from scratchpad.

The archived `attempt4-flight-receipt.json` is the flight receipt verbatim. Its bulk (63 KB of its
81 KB) is `close_receipt.timings`, a list of per-request latency floats; a structural scan confirms
the file contains **no string longer than 120 characters**, i.e. no response text — it is a receipt,
not a trace.

## Launcher provenance

The attempt-1 launcher was copied to scratchpad `pslufly4` and the only edits were the scratchpad
path itself (`env.sh`'s `SCRATCH` and the `source` line of the wrappers, `pslufly`/`pslufly3` →
`pslufly4`). All five `.py` files are **byte-identical** to `launcher/`, confirmed by `cmp` against
the archived copies, so `launcher/`'s manifest hashes still describe the code that flew.

New this attempt, archived alongside (all scratchpad-only, none of them repository code):

| file | purpose |
|---|---|
| `attempt4-confinement-sanity.py` / `.log` | the pre-flight proof that the attempt-3 blocker is gone |
| `attempt4-hygiene.sh` | bytecode / GPU / feature-cache / model / orphan-process hygiene |
| `attempt4-arm-accounting.sh` / `.log` | structural row accounting that never opens a result field |
| `attempt4-postflight.log` | receipt, artifact shapes, ledger and tree verification after close |
| `attempt4-manifest-check.log` | trace manifest, session receipt and plan fields |
| `attempt4-flight.log` | the full 363-request operational log (index, media path, latency, length) |
| `attempt4-flight-receipt.json` | the flight receipt verbatim |

## What the read mission needs

- run id `SAEA-PROBE-pslu-n60`, attempt id **`attempt-20260818T010218Z-4c97cb`**;
- input `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/attempt-20260818T010218Z-4c97cb/outputs.jsonl`
  (363 rows) plus `predicted-scenarios.json`;
- identity to check against the registration: config `a72c7a6c…`, protocol `5a9d989d…`, split
  `fc9de436…`, trace manifest `bc25cb53…`;
- the exposure row is still `consumed = no`; the single registered read session flips it.

Nothing about the flight is known to compromise the read: all six arms flew over the identical
frozen 60, no request failed, no response was replayed from an earlier attempt (attempts 1–3 made
zero core contact, so no stale cache exists), and no result was observed by flight operations.
