# P-SLU flight attempt 3 (2026-08-18) — NOT FLOWN (aborted on request 1; zero core contact)

This file is **appended** to the 2026-08-17 attempt-1 / attempt-2 archive; no earlier file was
modified. It records the third flight attempt of the registered probe
`docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md`, exposure row
`SAEA-PROBE-pslu-n60`.

**Zero frozen-core contact occurred again, for a third distinct reason.** The two blockers found by
attempts 1 and 2 are both cleared and were re-verified before launch; the flight reached
`FLIGHT START` for the first time, built request 1, and was refused by the payload media-confinement
rail *before the request left the process*. `close_receipt.cost` reports `calls_used: 0` and
`audio_seconds_used: 0.0`, `responses.jsonl` was never created, the campaign feature cache is still
empty, and the exposure row remains `consumed = no` with the whole 450-call allowance intact.

The launcher archived with attempt 1 was run **unmodified** (provenance below).

## Identity

| field | value |
|---|---|
| run id | `SAEA-PROBE-pslu-n60` |
| attempt id | `attempt-20260818T004057Z-7edb9c` |
| config hash | `a72c7a6cadda40a852a766e8eed9b99f0a9d0daf7c7784f9fa01780df9f5ee4d` |
| protocol hash | `5a9d989d9e628f91fd6b49c6eb400b29b9556b80583b14d4dfc8fe0b6de8d72c` |
| split identity hash | `fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5` |
| trace manifest hash | `3bb15c2b443688a275f16088e8b8113f0e2cf3f9533785b1ddefdd839b6a20c1` |
| study commit during flight | `8ae0645` (tree clean before, during and after) |

Config and protocol hashes are byte-identical to attempt 2, so the identity that flew is the
registered one: nothing about the run identity drifted while the two earlier blockers were fixed.

## Both prior blockers: CLEARED and verified

1. **Attempt-1 blocker — SLURP absent from the D1 media-identity closure.** Cleared at `f6a98e5`.
   Archived probe re-run unchanged (`attempt3-d1-probe.log`):

   ```
   resolve_media_identity_carrier('slurp') -> slurp
   verify_media_identity('slurp'): PASS
   ```

2. **Attempt-2 blocker — SLURP sample ids are not path-safe slice directory components.** Cleared at
   `fdf1ed8` / `3022cca` / `8ae0645`, which give `core/model/slices.py` a path-safe addressing token
   (`_slice_token`) distinct from the identity string. Measured before launch on the exact id that
   aborted attempt 2 (`attempt3-slice-sanity.log`, source `attempt3-slice-sanity.py`):

   ```
   slice_relpath('slurp:devel:005518:audio-1490203960', 0)
     -> derived/obs-slices/SAEA-PROBE-pslu-n60/slurp_devel_005518_audio-1490203960-44a26008c62b/i0000.wav
   slice_relpath('tier1_direct:000001', 0)
     -> derived/obs-slices/SAEA-PROBE-pslu-n60/tier1_direct_000001-b7cce6f6fdc7/i0000.wav
   ```

   Colon-free, path-safe and injective (the near-collision id `slurp:devel:005518:audio:1490203960`
   maps to a different directory). The Audio2Tool id shape is covered by the same fix.

   Confirmed again in flight, not merely in a probe: all three registered silence-swap slices
   registered and their `.wav` files were written under
   `derived/obs-slices/SAEA-PROBE-pslu-n60/` (`attempt3-flight.log`, and the three files are listed
   in `attempt3-carrier-root-probe.log`).

## Pre-flight: CLEAN

`attempt3-preflight.log` — every registered fact reproduced again, all model-free: 8,690 devel
samples loaded and 60 selected in the frozen order, **60/60 flac present**, **182.26 s** total audio
(mean 3.04 s), **89 gold slots**, **18** distinct gold scenarios, roster table legal (18 scenario
rosters / 55 global types / 100 dose-capped entries / 18 derangement keys), all 3 silence-swap ids
inside the frozen 60, exposure row present exactly once with `consumed = no` and budgets
450 / 1500 / 0.5, and the `ExecutionPlan` validating as `bounded-discovery-probe` / `discovery`.

`attempt3-preflight.log` and `attempt3-d1-probe.log` are **byte-identical** to their attempt-2
counterparts (`743c9ccc…` and `e97b77af…` in `MANIFEST.sha256` — the same hash appears twice each),
so the pre-flight and the D1 probe reproduced bit-for-bit across two independent runs on different
days.

Hygiene before launch (`attempt3-env-probe-before.log`, script `attempt3-env-probe.sh`):
`PYTHONDONTWRITEBYTECODE=1` exported in every flight shell; **zero** `*.pyc` and **zero**
`__pycache__` under `src/`; campaign feature cache `/home/chao/feat-cache/slurp-q4km` empty
(0 entries); legacy `/home/chao/feat-cache/q4km` 26 GB / 34,350 entries, dir mtime 2026-08-16 —
never opened; no orphaned `llama-server`; GPU idle at P8 / 195 MHz / 322 MiB before launch, with no
power-cap event at any point.

## Runtime: healthy and correctly pinned

`attempt3-flight-receipt.json` (`session` block) — identical pins to attempt 2:

- binary `/home/chao/llama.cpp-featcache/build/bin/llama-server`, sha256
  `097c96ec5a3f576f378d4d5e103928bf070647fdcc1f015eacb839503e121c68`;
- model resolved to the **ext4** copies under `/home/chao/models/…`, never `/mnt/e`, both per-file
  SHA-256 matching `docs/receipts/runtime-q4km-featcache.json`: `0751c279…066d` (Q4_K_M) and
  `f0dfe825…2883` (mmproj bf16);
- feature cache directed to `/home/chao/feat-cache/slurp-q4km`; the legacy 26 GB cache was never
  opened (re-verified after the abort: still 26 GB / 34,350 entries, mtime unchanged).

## Blocker: the SLURP lock entry carries two disagreeing path authorities

Request 1 was refused inside `core/model/paths.py::_resolve_confined` (`attempt3-flight.log`):

```
[00:42:16Z] req 0001 FAILED after 0.0s media=datasets/slurp/slurp_real/audio-1495375974.flac :: FrozenCoreError
[00:42:16Z] FLIGHT ABORTED: FrozenCoreError: payload media_relpath escapes its confined root
  /mnt/e/.../speechrl-data/repos/slurp/scripts/audio: 'datasets/slurp/slurp_real/audio-1495375974.flac'
```

Two governed resolvers disagree about where SLURP audio lives, and both read the **same** lock entry:

| consumer | resolves from | result |
|---|---|---|
| `data/slurp.py::_governed_roots` (the loader, hence every `media_relpath`) | `annotations.governed_copy` (`datasets/slurp/metadata`) minus its `/metadata` suffix | `datasets/slurp` |
| `rails/core_client.build_payload_binding`'s `carrier_root` — canonically `data.lock.asset_dir(lock, key, root)`, exactly as `core/driver/run.py:400` does it | `local_subdir` | `repos/slurp/scripts/audio` |

`_resolve_confined` resolves both sides **and follows symlinks** before comparing, so the refusal
proves the two trees are physically distinct directories, not one tree behind a link. Measured
directly (`attempt3-carrier-root-probe.log`, script `attempt3-carrier-root-probe.sh`, read-only):

- `readlink -f datasets/slurp` → `…/speechrl-data/datasets/slurp`;
  `readlink -f repos/slurp/scripts/audio` → `…/speechrl-data/repos/slurp/scripts/audio`. No link.
- **Both** trees hold `slurp_real/` with **72,395** files each, and the request-1 file
  `audio-1495375974.flac` exists in both at the identical size (51,039 bytes).
- `datasets/slurp` additionally holds `metadata/`, `annotation-receipt.json` and an `audio/` subdir.

This reproduces, at flight time, the redundancy the umbrella lock already recorded in its own
amendment note: "The same audio payload is reachable at both `datasets/slurp` and
`repos/slurp/scripts/audio` as distinct files rather than links … Nothing was deleted: reclaiming
this space is an owner decision, and the entry's `local_subdir` still points at
`repos/slurp/scripts/audio`."

SLURP is the **only** carrier with this split, which is why no rail ever hit it before
(`attempt3-carrier-root-probe.log`):

```
slurp:               local_subdir='repos/slurp/scripts/audio'      governed_copy='datasets/slurp/metadata'
earnings21-original: local_subdir='datasets/earnings21-22/earnings21'  governed_copy=None
conec:               local_subdir='datasets/conec'                 governed_copy=None
```

For every carrier that flies today, `local_subdir` *is* the tree the loader reads, so confinement
aligns silently. SLURP is the first carrier whose loader was pointed at a second governed tree.

Each side is deliberate, with its reason recorded in its own source:

- the loader points at `datasets/slurp` **on purpose** — `data/slurp.py`'s module docstring states it
  mirrors "the SAME base the governance receipt already verified", because
  `datasets/slurp/annotation-receipt.json` reconciled every `recordings[].file` reference against
  exactly that tree's `slurp_real`/`slurp_synth` subdirectories (141,648 / 141,648 across all four
  splits);
- `build_payload_binding`'s docstring states `carrier_root` "is the SAME per-carrier subdirectory
  `data.lock.asset_dir(lock, carrier_lock_key, root)` would resolve", and the launcher passes
  exactly that — the same call the canonical non-rails caller `core/driver/run.py:400` makes.

So the launcher is not passing a wrong argument: it is passing the only sanctioned one, and the
loader is reading the only tree its own governance receipt covers.

### Why no workaround was taken

A read-only sweep established that **no sanctioned override hook exists on either side**:

- `_governed_roots(lock, root)` takes no audio-root parameter and derives the root solely from
  `annotations.governed_copy`; `SlurpAdapter.__init__` accepts only `lock`, `root` and `repo_root`,
  so the loader's base cannot be redirected by any caller.
- `carrier_root` is a positional fact of `PayloadBindingContext`, validated only as "beneath
  `data_root`" (`core/base.py:323`), so the launcher *could* be made to hand in
  `root / "datasets/slurp"` — and confinement would then pass.

That last option was deliberately **not** taken. It does not disable the rail, but it does resolve a
contradiction between two governance records by implementer fiat: it would fly audio bytes from the
tree the umbrella lock does **not** declare as the carrier's materialized directory, while the
umbrella lock is this program's single live source of dataset identity and its `local_subdir` is
what `asset_dir` — the canonical carrier-root resolver — returns. Choosing which of the two trees is
the carrier root is a governance decision (the lock's own note leaves the duplication as a pending
owner decision), not a flight-operations one. The same applies to editing `local_subdir`, to
repointing `_governed_roots` at `asset_dir`, and to deleting either tree.

Note for whoever fixes it: because both trees hold the same 72,395 real recordings and D1 pins
per-sample media identity by **sha256 keyed on sample id** (not by path — `carriers.slurp.layers.
media` in `docs/receipts/artifacts/d1-identity.json` carries `id`/`sha256`/`bytes` only), either
tree can satisfy the D1 rail on bytes. The choice is therefore about governance and storage, not
about identity provability, and it should be made once for both consumers rather than patched at
one call site.

## Cost

| quantity | registered ceiling | consumed this attempt | consumed to date |
|---|---|---|---|
| core calls | ≤ 450 | **0** | **0** |
| speech audio seconds | ≤ 1500 | **0** | **0** |
| GPU hours | ≤ 0.5 | **0** decode | **0** |

Wall clock launch → abort: **2 min 15 s** (00:40:01Z → 00:42:16Z), of which 55 s was the model-free
devel-split hash pass, 25 s the server spawn and 54 s the payload-binding media hashing. The server
was resident ≈ 64 s and idle after a ~6 s model load; the GPU never left P8 and no clock-lock
intervention was needed. Requests built 1, flown 0, replayed 0, failed 1 (refused pre-transport),
resumes 0. The exposure row `SAEA-PROBE-pslu-n60` stays `consumed = no`.

## State left behind

- `$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/attempt-20260818T004057Z-7edb9c/` holds
  `…plan.json`, `…config-values.json`, `…session-receipt.json`, `…server.log`,
  `…trace-manifest.json` and `flight-receipt.json` (status `ABORTED`). No `responses.jsonl`, no
  `outputs.jsonl`, no `predicted-scenarios.json` — nothing for the one-shot read mission exists yet,
  and nothing was read by this agent.
- Three silence-swap slice `.wav` files under
  `$SPEECHRL_DATA_DIR/derived/obs-slices/SAEA-PROBE-pslu-n60/` (derived data, outside Git).
- Unlike attempt 2, the abort landed inside the launcher's own `try/except`, so `client.close()` ran
  and a close receipt exists (`trace_manifest_hash` above).
- No orphaned `llama-server`; campaign feature cache still empty; legacy cache untouched; the study
  working tree stayed clean for the whole attempt and the launcher ran from scratchpad.

## Launcher provenance

The attempt-1 launcher was copied to scratchpad `pslufly3` and the only edits were the scratchpad
path itself (`env.sh`'s `SCRATCH` and the `source` line of the three `run_*.sh` wrappers,
`pslufly` → `pslufly3`) — **4 changed lines**, confirmed by `diff -r` against `launcher/`. No `.py`
file was touched, so `launcher/`'s manifest hashes still describe the code that ran.

New this attempt, archived alongside (all scratchpad-only, none of them repository code):

| file | purpose |
|---|---|
| `attempt3-run-flight.sh` | the flight wrapper `launcher/` never shipped (fresh run, or `--attempt-id` resume) |
| `attempt3-slice-sanity.py` | pre-flight proof that the attempt-2 blocker is really gone |
| `attempt3-env-probe.sh` | bytecode / feature-cache / model / orphan-process hygiene |
| `attempt3-carrier-root-probe.sh` | the two-path measurement behind this blocker |

## Archive repair: the evidence logs were never committed

`.gitignore:39` ignores `*.log`, and neither attempt 1 nor attempt 2 force-added its logs — so every
`.log` line in `MANIFEST.sha256` hashed a file that existed only in the working tree, and a fresh
clone could verify none of them. Other campaigns in this repository do track their evidence logs
under `docs/checks/` (8 such files), so the omission was local to this directory, not the convention.

This commit force-adds every `.log` in this directory — attempts 1, 2 and 3 alike — with no change to
any byte of any existing file. The manifest hashes were already correct; they are now backed by Git
blobs, which is what makes them checkable.

## What the next attempt needs

1. **One governance decision, made once, for both consumers**: which tree is the SLURP carrier root —
   `repos/slurp/scripts/audio` (today's `local_subdir`, hence `asset_dir`, hence every rails
   `carrier_root`) or `datasets/slurp` (today's `annotations.governed_copy` parent, hence every
   `media_relpath` the loader emits, and the tree the annotation receipt reconciled). Then make the
   two resolvers agree — by amending the umbrella lock entry, or by repointing `_governed_roots`,
   whichever the decision selects. Both trees carry the same 72,395 real recordings, so either
   choice preserves D1 identity; the duplication itself (26 GB + 13 GB) is a separate, already-noted
   owner decision.
2. Nothing else is known to be in the way: D1 is closed, slice addressing is fixed, the pre-flight is
   clean, the runtime starts, the model identity verifies, the silence-swap controls register and
   write, and the launcher is proven all the way to a fully built request 1. The registered budgets
   remain entirely intact, so the next attempt inherits the whole 450-call allowance.
