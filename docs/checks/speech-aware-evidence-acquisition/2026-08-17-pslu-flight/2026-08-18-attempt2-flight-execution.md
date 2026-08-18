# P-SLU flight attempt 2 (2026-08-18) — NOT FLOWN (aborted after server start; zero core contact)

This file is **appended** to the 2026-08-17 attempt-1 archive; none of that attempt's files were
modified. It records the second flight attempt of the registered probe
`docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md`, exposure row
`SAEA-PROBE-pslu-n60`.

**Zero frozen-core contact occurred again, for a different reason.** A `llama-server` *was* spawned
this time and the model *was* loaded, but the launcher aborted while registering the three
registered silence-swap slices — **before the first request was built**. `responses.jsonl` was never
created, the campaign feature cache is still empty, and the exposure row remains `consumed = no`.

The launcher archived with attempt 1 was run **unmodified**. It was copied to a scratchpad working
directory and the only edits were the scratchpad path itself (`env.sh`'s `SCRATCH`, and the
`source` line of the three `run_*.sh` wrappers, `pslufly` → `pslufly2`); no `.py` file was touched,
so `launcher/`'s manifest hashes still describe the code that ran. The study working tree was clean
at `f6a98e5` before, during and after the attempt.

## Attempt-1 blocker: CLEARED and verified

The attempt-1 refusal (SLURP absent from the D1 media-identity closure) is fixed at commit
`f6a98e5`. Re-running the archived probe unchanged (`launcher/probe_d1.py`, evidence
`attempt2-d1-probe.log`, re-run again after the abort with the same result):

```
resolve_media_identity_carrier('slurp') -> slurp
verify_media_identity('slurp'): PASS
```

## Pre-flight: CLEAN

`attempt2-preflight.log` — every registered fact reproduced again, all model-free: 8,690 devel
samples loaded and 60 selected in the frozen order, **60/60 flac present**, **182.26 s** total audio
(mean 3.04 s), **89 gold slots**, **18** distinct gold scenarios, roster table legal (18 scenario
rosters / 55 global types / 100 dose-capped entries / 18 derangement keys), all 3 silence-swap ids
inside the frozen 60, exposure row present exactly once with `consumed = no` and budgets
450 / 1500 / 0.5, and the `ExecutionPlan` validating as `bounded-discovery-probe` / `discovery`.
The split-identity-hash cell repaired before attempt 1 now matches the plan verbatim.

Identity assigned for this attempt:

| field | value |
|---|---|
| run id | `SAEA-PROBE-pslu-n60` |
| attempt id | `attempt-20260818T000441Z-92584e` |
| config hash | `a72c7a6cadda40a852a766e8eed9b99f0a9d0daf7c7784f9fa01780df9f5ee4d` |
| protocol hash | `5a9d989d9e628f91fd6b49c6eb400b29b9556b80583b14d4dfc8fe0b6de8d72c` |
| split identity hash | `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` |

## What the runtime stack proved before the abort

The server side is healthy and correctly pinned — this attempt is the first evidence that the
receipt-pinned runtime starts for this probe at all (`attempt2-session.log`):

- binary `/home/chao/llama.cpp-featcache/build/bin/llama-server`, sha256
  `097c96ec5a3f576f378d4d5e103928bf070647fdcc1f015eacb839503e121c68`, llama.cpp build commit
  `5d9dfcb58ea860295da8fc93c7b5bed9e2c71151`;
- model resolved to the **ext4** copies under `/home/chao/models/...`, never `/mnt/e`, with both
  per-file SHA-256 matching `docs/receipts/runtime-q4km-featcache.json` exactly:
  `0751c279…066d` (Q4_K_M) and `f0dfe825…2883` (mmproj bf16);
- feature cache directed to `/home/chao/feat-cache/slurp-q4km`; the legacy 26 GB
  `/home/chao/feat-cache/q4km` was never opened (`attempt2-cache-integrity.log`);
- `model loaded` in 5.9 s, 4 slots at `n_ctx` 12288, `server is listening`, `all slots are idle`.

## Blocker: SLURP sample ids cannot address an OBS slice

The launcher aborted at the first of the three registered silence-swap registrations
(`attempt2-flight-abort.log`):

```
File ".../rails/silence_swap.py", line 86, in build_silence_swap_slice
  slice_relpath = registry.slice_relpath(sample_id, iteration)
File ".../core/model/slices.py", line 154, in slice_relpath
  raise FrozenCoreError(f"slice sample_id {sample_id!r} is not path-safe")
FrozenCoreError: slice sample_id 'slurp:devel:005518:audio-1490203960' is not path-safe
```

`SliceRegistry.slice_relpath` uses the sample id verbatim as a **directory component** of
`derived/obs-slices/<run_id>/<sample_id>/i<NNNN>.wav` and screens it with
`_PATH_SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")` (`core/model/slices.py:63`). SLURP sample
ids are `carrier:split:index:stem`, so every one of the 60 fails the screen.

This is a **policy** constraint, not a filesystem one: a directory named
`slurp:devel:005518:audio-1490203960` creates and accepts a file without error on both the NTFS
data root (`/mnt/e`, via DrvFs) and ext4, measured directly and reproducibly
(`attempt2-pathsafety-fs-probe.sh`, output `attempt2-pathsafety-fs-probe.log`; the probe cleans up
after itself and touches no project data).

SLURP slice support is unwritten work rather than an unrun generator. A read-only sweep of the
source established that **no sanctioned path-safe identifier exists anywhere in the repository**:

- `_PATH_SAFE` occurs in exactly three places, all in `core/model/slices.py` (`:63`, `:137`, `:153`),
  and every one is a **validator** — there is no slugify, hash-directory, alias table or id map, and
  `SliceRecord` has no token field beside `sample_id`.
- `build_silence_swap_slice` (`rails/silence_swap.py:62-71`) has **no alias parameter**; it hands
  `sample_id` straight to `registry.slice_relpath` (`:86`) and stores it raw on the record (`:93`).
- `parent_facts` is keyed by the **raw** id on both the rails path
  (`rails/core_client.py:233-235`) and the non-rails path (`core/driver/run.py:428`), and
  `register()` looks the record up by `record.sample_id` (`slices.py:175`). So one string must
  simultaneously satisfy the dict lookup and the path screen.
- `register()` additionally **re-derives** the path itself (`slices.py:233`) and refuses any
  mismatch, so a hand-built record cannot smuggle a different `media_relpath` past it. There is no
  escape hatch.
- Every sample directory that exists under `derived/obs-slices/` across ~90 historical runs is a
  bare numeric earnings id (`4366522`, `4453225`, …) — path-safe by construction, which is why the
  rail has never hit this before.

**Audio2Tool is affected identically**: `data/audio2tool.py:267` builds `f"{tier}:{item_id:06d}"`
(e.g. `tier1_direct:000001`), also colon-bearing. Fixing this unblocks slices for both carriers.

Why the gap was invisible until a server actually ran: the only test that pairs silence-swap with
SLURP, `tests/unit/test_pslu_flight.py:379`, **hardcodes** the string
`"derived/obs-slices/run-x/slurp:devel:000101:audio-101/i0000.wav"` and passes it to a mock client —
it never constructs a `SliceRegistry` or calls `slice_relpath`, so it asserts the very path the real
registry refuses to produce. Every real test of `build_silence_swap_slice`
(`tests/unit/test_rails_silence_swap.py:76,113,134`) passes the synthetic path-safe id `"s1"`, and
there is no negative test for the path-safety refusal at all.

### Why no workaround was taken

Both available shortcuts are outside flight-operations authority, and each would fly something
other than the registered protocol:

1. **Sanitising the id inside the launcher.** Impossible without breaking a rail, per the above:
   `parent_facts` and `register()` key on the raw id while `slice_relpath` screens the same string,
   so a colon-free id either fails the binding lookup or, if the record carried it, disables exactly
   the rail guaranteeing a slice belongs to a verified split sample.
2. **Dropping the silence-swap control.** Silence-swap on 3 seeded A1' samples is registered in
   §2 of the preregistration and is load-bearing for the **VOID** branch rule in §4 ("silence-swap
   answers persist unchanged"). Flying 360 requests without it is a different protocol than the one
   registered, which the implementer may not decide unilaterally.

The fix is a design decision in `core/model/slices.py` — give the registry a path-safe *addressing
token* distinct from the identity string, with the raw id staying as the binding key and in the
record and trace, so `slice_relpath` stops requiring the identity to double as a filename. Note that
the obvious shortcut is wrong: `SlurpSample.utterance_id` is path-safe but **not unique** (one
`slurp_id` yields one record per recording, which is exactly what the `:{file-stem}` suffix in the
sample id disambiguates), so it cannot serve as the directory name. A derived token such as
`{slurp_id:06d}-{stem}` would work, but nothing in the repository derives one today.

This also touches a standing design record: `docs/readiness/2026-08-08-ojw-rebuild-notes.md:198-203`
asserts slice-file collision-freedom **because** "the sample id is a path component". That was
written when only the numeric-id earnings carriers existed; whoever adds the token should supersede
that reasoning rather than silently invalidate it.

## Cost

| quantity | registered ceiling | consumed this attempt |
|---|---|---|
| core calls | ≤ 450 | **0** |
| speech audio seconds | ≤ 1500 | **0** |
| GPU hours | ≤ 0.5 | **0** decode; server resident ≈ 96 s wall, idle after a 5.9 s load |

Wall clock from launch to abort: **2 min 50 s** (00:03:50Z → 00:06:40Z), of which 51 s was the
model-free devel-split hash pass. Requests flown 0, replayed 0, failed 0, resumes 0. The exposure
row `SAEA-PROBE-pslu-n60` stays `consumed = no`.

## State left behind

- `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/attempt-20260818T000441Z-92584e/` holds only
  `…plan.json`, `…config-values.json`, `…session-receipt.json` and `…server.log`. No
  `responses.jsonl`, no `outputs.jsonl`, no `flight-receipt.json` (the abort raised before the
  launcher's own try/except, so `client.close()` did not run and no close receipt exists).
- No orphaned `llama-server`; VRAM released to idle (322 MiB) and the GPU returned to P8 with no
  power-cap event at any point during the attempt.
- The study working tree stayed clean for the whole attempt; the launcher ran from scratchpad.

## What the next attempt needs

1. A path-safe slice-addressing token in `core/model/slices.py`, with the raw sample id preserved as
   the registry binding key and in the record/trace. It should cover Audio2Tool as well, since
   `data/audio2tool.py:267` produces colon-bearing ids for the same reason.
2. A test that exercises `build_silence_swap_slice` with a **colon-bearing** sample id through a
   real `SliceRegistry`, plus a negative test for the path-safety refusal — neither exists today,
   and `tests/unit/test_pslu_flight.py:379` should stop hardcoding a slice path the registry cannot
   produce, because that mock is what hid this defect behind a green suite.
3. Nothing else: D1 is closed, the pre-flight is clean, the runtime starts, the model identity
   verifies, and the launcher is otherwise proven up to the first request. The registered budgets
   are fully intact, so the next attempt inherits the whole 450-call allowance.
