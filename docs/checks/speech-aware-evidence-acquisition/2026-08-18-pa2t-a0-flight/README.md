# P-A2T Stage-1 A0 baseline flight — PRE-FLIGHT CLOSED, NOT FLOWN

Date: 2026-08-18. Run id: `SAEA-BASE-a2t-a0-400`. Profile: `baseline-reproduction`.
Status: **NOT FLOWN — zero core contact. The carrier-scope gate refuses the touch.**

The flight this directory prepares is item 4 of the 2026-08-17 night restructure
(`docs/readiness/2026-08-17-pa2t-preregistration-draft.md` §8): the A0 zero-supply
baseline re-fly on the frozen 400-item Audio2Tool discovery split, which measures the
real tool-acc/EM gap and yields the Stage-2 headroom sample list. Everything the flight
needs is built, verified and committed. One governance precondition is not met, and it
is not the flying agent's to grant.

## The blocker

`contracts.gate_exposure._resolve_carrier_dataset_entry` refuses, model-free, before any
socket is opened:

```
GateClosed: carrier lock key 'audio2tool' profiles ['local-candidates'] do not intersect
this study's speech-only scope ['speech-aware-core', 'speech-aware-diagnostics',
'speech-aware-secondary', 'speech-aware-small-public']; model touch refused
```

The umbrella lock still files Audio2Tool as `lifecycle: LOCAL_CANDIDATE`,
`profiles: ["local-candidates"]` — a profile whose own catalog description reads
"presence does not authorize an experiment". `ALLOWED_CARRIER_PROFILES`
(`gate_exposure.py:27-34`) is a literal frozenset with no env override, config hook or
allowlist extension anywhere in `src/`, `scripts/` or `configs/`; the gate also fails
closed on a missing `profiles` field, so deleting the field is not a path either. There
is no bypass, by construction.

`preflight-carrier-scope-control.log` shows the refusal is carrier-specific and not an
artifact of the pre-flight harness: `slurp`, `earnings21-original` and `conec` all
resolve IN SCOPE through the same call; `audio2tool` alone is refused.

## Why this was not repaired in flight

`docs/readiness/HANDOVER.md` (lines 100-103) names this exact case and forbids it:

> Never modify `docs/datasets.lock.json`: the missing `speech-aware-*` profiles on
> `slurp`, …, `audio2tool`, `voiceagentbench` are why the gate cannot see them, but
> assigning a profile is a data-identity change requiring the umbrella's formal path and
> owner approval.

The blocker is long-standing and already queued as an owner decision —
`docs/readiness/2026-08-09-exploration-plan.md:31` records audio2tool as
**blocked → lock profile + D1**, and `docs/readiness/2026-08-11-validation-plan-wa-wd.md:141`
parks it as *"Lock-profile batch (slurp, spoken-squad, big-bench-audio, audio2tool →
`speech-aware-*`)"*.

The 2026-08-15 owner amendment (Amendment 1, umbrella
`wiki/experiments/speech-aware-evidence-acquisition/2026-08-15-owner-go-dual-track-agentic.md`)
admits the bounded Audio2Tool probe, and SLURP's own promotion to
`speech-aware-secondary` (umbrella commit `1677b07`) was justified by citing that same
dated owner record in the entry's `research_role` field. So the substantive authority
plausibly already exists. But that promotion rode inside a broader acquisition-wave
commit and got no dedicated amendment change-kind of its own, so treating it as blanket
authority to repeat the move would infer more sanction than the record shows — while
`2026-08-11-validation-plan-wa-wd.md:141` explicitly parks the decision with the owner.
`git log -S audio2tool -- docs/datasets.lock.json` returns exactly one commit, the
original consolidation: nothing has touched the audio2tool entry at any point after the
2026-08-15 amendment.

**A documentation gap worth closing.** The currently-live P-A2T binding docs have lost
this blocker: `docs/readiness/2026-08-17-g0-binding-tables.md` §1.9 lists B1-B6 and
`configs/probes/g0-binding/pa2t-binding.json` lists B1-B5, and none of them mention the
lock profile. It survives only in the older 08-09/08-11 readiness docs and HANDOVER.md.
A flight agent reading only the binding tables would build the whole launcher — as this
one did — before discovering the refusal.

## What IS closed (all model-free, all verified this session)

| Precondition | Result |
|---|---|
| Exposure row committed before any core contact | `017d537` — `SAEA-BASE-a2t-a0-400`, 15 columns, parses as exactly 1 row, carrier cell binds unambiguously to `audio2tool`, consumed=no |
| Frozen split resolves | exactly ONE audio2tool receipt declares `split_role=discovery`; `load_split('discovery')` returns 400 samples, 8 tiers x 50, 400/400 media present |
| Split identity | receipt hash `e1d751e6…332c` matches both binding JSONs and the ledger cell verbatim (64-hex) |
| Real audio total | **2159.69 s** (mean 5.399, max 35.714) — the binding JSON knew only 1801.3 s, which covered the 350 items carrying a top-level duration |
| D1 media identity | `verify_media_identity('audio2tool')` **PASS** on two real frozen-split samples; unlisted sample id correctly refused. `d1-identity.json` carries audio2tool with 400/400 media entries (the `f6a98e5` commit message's "audio2tool partial (1 sample)" understates the artifact it committed) |
| Bytecode hygiene | 0 `.pyc` under `src/`; `PYTHONDONTWRITEBYTECODE=1` in `launcher/env.sh` |
| Feature cache | `/home/chao/feat-cache/audio2tool-q4km` created cold; legacy `q4km` (26 G) and `slurp-q4km` (23 M) untouched. `flight_identity.resolve_feat_cache_dir` hard-fails on any other directory |
| GPU | idle, P8, 392 MiB / 24463 MiB, 49 C |
| ExecutionPlan | validates as `baseline-reproduction` / `discovery`, calls 420 / audio 3000 s / 1.5 GPU-h, protocol hash `c4227ac9…`, config hash `29dcf6cd…` |
| Payload binding | builds over all 400 ids, sample rate 24000 Hz uniform |
| Contract tests | `tests/contract` 260 passed |
| Gate dry-run | **REFUSED** — the one open item (above) |

## The context-overflow defect this pre-flight caught

The committed model fragment `configs/model/q4km-featcache.json` carries
`-c 49152 -np 4`. llama-server divides `-c` across parallel slots, so that is **12288
tokens per slot** — the archived P-SLU attempt-2 log records exactly that ("4 slots at
n_ctx 12288"). This flight's system instruction is the full 152-tool registry:
**50,413 chars, ~12.6k estimated tokens** before audio and before any output. Every one
of the 400 requests would have overflowed its slot.

`launcher/flight_identity.py` therefore applies a fourth documented delta beyond the
three the archived P-SLU launcher used: **`-np 4` → `-np 1`**. It is memory-neutral
(total `n_ctx`, hence total KV cache, is unchanged), costs no throughput (the rails
`FrozenCoreClient` issues requests strictly sequentially, so slots 2-4 were never
usable), and additionally lets llama-server's longest-common-prefix slot cache reuse the
identical registry prefill across consecutive requests instead of re-paying it in four
round-robin slots. `_apply_np_delta` fails closed if the committed fragment ever stops
carrying exactly one `-np 4` pair. The delta is disclosed in the exposure row.

## Budget refinements carried into the row

Both are refinements the flight config's own `cost_budget` note explicitly invites.

- **Speech audio seconds 2400 → 3000 (up).** The config's 2400 derived from the
  binding's partial 1801.3 s. The adapter resolves all 400 items at a measured
  2159.69 s. Worst case inside the call budget is 2159.69 + 20 retries each bounded by
  the split's own longest item (35.714 s) = 2874.0 s, so 3000 is the smallest round
  ceiling that cannot be crossed before the call budget stops the run. 2400 would have
  been crossed by ~240 s of retries.
- **GPU hours 2.0 → 1.5 (down).** From the config's acknowledged placeholder to the
  mission's registered ceiling.

## To fly this, once the lock entry is admitted

The launcher is complete and needs no further work. After the umbrella lock gives
`audio2tool` a `speech-aware-*` profile through the formal path:

```bash
bash <scratch>/a2tfly2/run_preflight.sh     # must print PRE-FLIGHT CLEAN
bash <scratch>/a2tfly2/run_flight.sh        # fresh attempt
bash <scratch>/a2tfly2/run_flight.sh <id>   # resume: cached responses replayed, no re-contact
```

`launch_pa2t_a0.py` enforces two hard operational ceilings before the request that would
cross them — 450 requests and 1.5 h wall clock — independently of the contract's own
call/audio metering, and appends every response to `responses.jsonl` for fail-closed
resume under the one registration. It never reads a result: `outputs.jsonl` is written
for the separately-registered read mission, and the health log carries only request
index, sample id, latency, ok/fail and response length.

The exposure row stays registered and unconsumed; a later flight reuses it as-is.

## Files

- `launcher/` — the complete flight launcher, pre-flight, D1 probe, controls and shells
- `preflight-split-measurement.log` / `.json` — model-free split identity and audio total
- `preflight-d1-probe.log` — D1 media identity PASS plus negative control
- `preflight-carrier-scope-control.log` — the four-carrier scope control
- `preflight-REFUSED.log` — the full pre-flight, green on every axis but the gate dry-run
- `MANIFEST.sha256` — hashes of everything above
