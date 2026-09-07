# Derived media roots bind — the defect, the rule, and the check that was missing

**Model-free repair. Zero model contacts, zero sockets, zero GPU. No exposure row is due.**
Code commit under proof: `b1275380`. Receipt:
`docs/checks/speech-aware-evidence-acquisition/2026-09-07-derived-media-confinement/`
(`derived-media-confinement.json` + `MANIFEST.sha256`); re-runnable as
`python scripts/checks/derived_media_confinement_check.py`.

---

## 1. The defect

Every cross-carrier derived-media population writes its files under
`$SPEECHRL_DATA_DIR/derived/<variant>/` — never under the carrier's own asset directory — and each
declares that root in its own dataset fragment beside the hash-pinned D1 media supplement that
vouches for the files:

| fragment key | fragments | derived root |
| --- | --- | --- |
| `derived_media_subdir` | `slurp-speech-native-dev1000-tail2s` (+ `-smoke4`) | `derived/slurp-dev1000-tail2s-v1` |
| `a2t_calibration_derived_subdir` | `audio2tool-calibration-400-{tail2s,16k,16k-tail2s}` (+ `-smoke4`) | `derived/a2t-calibration-400-*-v1` |
| `e22_esb_derived_subdir` | the Earnings-22 ESB utterance fragments | `derived/e22-esb-utterances/*` |

`core.model._enforce_payload_binding` confined every outgoing payload's `media_relpath` to
`binding.carrier_root` alone — `datasets/slurp`, `datasets/audio2tool` — with no notion of a
per-fragment derived root. So every derived row was refused the moment a real request was built:

```
FrozenCoreError("payload media_relpath escapes its confined root
  .../speechrl-data/datasets/slurp:
  'derived/slurp-dev1000-tail2s-v1/audio-1497266596@ts2.flac'")
```

Found by the SLURP `@ts2` packet-promotion gate run of 2026-09-07
(`SAEA-SN-DEV1000-TS2-PREPROCESS-V1`): 4 of 4 encode contacts failed client-side, the trace manifest
came back `{"records": {}}`, and the CPU sidecar's own log showed **no incoming request at all**.
Nothing was spent; the row's registered ceiling remains unconsumed.

## 2. Why nothing caught it, and why some cells flew anyway

Two agents, on two different days, ran `--preflight-only` and the zero-socket wire check and both
passed. Neither ever builds a payload: `_enforce_payload_binding` only runs inside `client.complete()`.
Media identity (`roster_samples`' own re-hash, the D1 supplement) passed too, because the files
genuinely are where the fragment says — the check that failed was confinement, not identity.

Derived-media cells DID fly, which is why the defect looked impossible. They fly because each of the
three flight-cell scripts carries its own private workaround: `run_slurp_closed_list_cell.py`,
`run_calibration_cell.py` and `run_e22_esb_cell.py` each read the fragment's derived-subdir key and
pass a `carrier_root_resolver` that REBINDS `carrier_root` itself to the derived root. Three copies
of one idea, and the wrong shape of it: it does not add the derived root, it swaps the carrier root
away, so a roster that legitimately mixed carrier and derived media could not be expressed at all.

The binding construction sites with no such seam refuse every derived row: `core/driver/run.py`
(`run_experiment`, whose loader-supplied `carrier_root` resolves the carrier's governed directory),
`core/driver/speech_native.py` (the speech-native profile — what packet preprocessing runs through,
and where the SLURP `@ts2` promotion died), and `core/flight/runtime.py`'s own default resolver
(`data.lock.asset_dir`) for any caller that passes no override.

## 3. The rule now in force

> A payload may name a `media_relpath` confined under the carrier root **or** under one of the
> derived media roots the composed dataset fragment itself declared — and only ever **after** the I4
> exact-relpath check, so the one file a payload may name is still exactly the one this run's
> verified split and the D1 supplement vouch for.

Mechanically:

* `core.base.PayloadBindingContext.derived_media_roots: tuple[Path, ...]`, validated the way
  `carrier_root` is — beneath `data_root`, and a **named variant directory strictly beneath**
  `<data_root>/derived/` (a bare `derived` would legalize every variant at once).
* `core.base.declared_derived_media_roots(values, data_root)` reads the three carrier spellings above
  and refuses, fail-closed, a declaration that is not a relative POSIX path under `derived/` or that
  carries no paired, hash-pinned D1 media supplement. Fragments that spell the supplement key as
  prose ("none, by design…") are caught by requiring the lowercase 64-hex digest beside it.
* `core.model.paths._resolve_confined_any` accepts any of several roots; with a single root it is
  byte-identical to `_resolve_confined`, refusal message included. Every root must itself resolve —
  an unavailable root is still a hard refusal, never skipped in favour of the next.
* Threaded through the three binding construction sites (`core/driver/run.py`,
  `core/flight/runtime.py`, `core/driver/speech_native.py`) and
  `rails.core_client.build_payload_binding`. A fragment that declares no such key contributes
  nothing, so every pre-existing binding is byte-identical in behaviour.

**Why this does not reopen the decoy hole** (the round-2 threat-model finding, IMPORTANT A in
`core/model/binding.py`): the widening happens strictly after the I4 exact-relpath check. By then the
payload's `media_relpath` has already been proven EQUAL to the single string the verified split holds
for that exact sample id, so the set of files a payload can name is unchanged at exactly one —
its own — whatever roots are legal. Confinement's remaining job is what it always was: prove that one
string cannot resolve, through symlinks and all, outside the controlled trees this run is bound to.

## 4. What the proof shows

`scripts/checks/derived_media_confinement_check.py` loads one real row per fragment through that
carrier's own roster loader (real bytes, re-hashed against the roster's record), builds a real
`PayloadBindingContext` through `rails.core_client.build_payload_binding`, and drives the production
`_enforce_payload_binding` with a payload carrying exactly the binding's own verified facts. It
constructs no transport and opens no attempt.

| fragment | declared root | real row | binds | pre-repair binding | decoy under the same root | another variant's declaration |
| --- | --- | --- | --- | --- | --- | --- |
| `slurp-speech-native-dev1000-tail2s` | `derived/slurp-dev1000-tail2s-v1` | `slurp:devel:000011:audio-1497266596@ts2` | PASS | refused | refused | refused |
| `audio2tool-calibration-400-tail2s` | `derived/a2t-calibration-400-tail2s-v1` | `tier1_direct:000045@ts2` | PASS | refused | refused | refused |
| `audio2tool-calibration-400-16k` | `derived/a2t-calibration-400-16k-v1` | `tier1_direct:000045@16k` | PASS | refused | refused | refused |
| `audio2tool-calibration-400-16k-tail2s` | `derived/a2t-calibration-400-16k-tail2s-v1` | `tier1_direct:000045@16k+ts2` | PASS | refused | refused | refused |
| `slurp-speech-native-dev1000` (comparator) | none | `slurp:devel:000011:audio-1497266596` | PASS | binds (unchanged) | refused | binds (unchanged) |

The "pre-repair binding" column is the defect reproduced against real bytes: the identical binding
with `derived_media_roots=()` still refuses with "escapes its confined root". The comparator column
is the regression fence: a carrier-rooted fragment declares nothing, and neither control changes it.

33 unit tests in `tests/unit/test_derived_media_confinement.py` cover the same four properties on
synthetic roots, plus the fragment reader's refusals and all 20 shipped fragments that declare a
derived key.

## 5. What the wire checks must now also exercise

This defect was invisible to every gate we had because **no model-free check ever built a payload**.
The preregistration
`docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md` (Audio2Tool wire-check
section) already ASSERTS "media-path confinement to the variant's own derived root" as something
preflight proves. It does not, and never did: preflight opens no `FrozenCoreClient` and calls no
`_enforce_payload_binding`. That assertion should be read as covered by this check, not by preflight.

**CLOSED (commits `d28a9ee8`, `0ca25b21`): the named follow-up -- extend
`scripts/cross_carrier_tail2s_wire_check.py` (and the other `*_wire_check.py` entry points) with a
payload-binding stage.** `rails.core_client.payload_binding_stage` is the shared function (one
canonical seam, beside `build_payload_binding`, which it calls unmodified): for a composed cell's own
real roster rows it builds a real `core.base.PayloadBindingContext` through the real carrier root
(never a per-script `carrier_root_resolver` swap) plus the fragment's own declared derived media
roots, then drives the production `core.model.binding._enforce_payload_binding` against a synthetic
payload for the first and last roster row (every row when the roster is 16 rows or fewer) -- zero
sockets, zero servers, zero model contacts, exactly as `scripts/checks/derived_media_confinement_check.py`
already proved, generalized into a call any wire check can make per cell instead of requiring every
new derived variant to be added to that check's own `FRAGMENTS` tuple.

It is now wired into all three wire-check entry points as a mandatory stage between the request half
and the seal half, so a cell is reported wire-ready only if its payloads BIND:
`scripts/cross_carrier_tail2s_wire_check.py` and `scripts/a2t_input_rate_16k_wire_check.py` run it
between `preflight` and `wire_check` in their per-cell loop (loading only the rows the stage will
check -- reading the A2T full/smoke4 population split from the experiment fragment's own
`populations` entry, since both variants share one 400-row roster receipt); `scripts/e21_kc_e1_wire_check.py`
runs it between its own "request half" and "evidence-rail half" blocks. A cell whose payloads do not
bind now fails the whole run.

Re-run (no `--write`, no receipt regeneration) on the repair worktree: `cross_carrier_tail2s_wire_check.py`
-- all 4 cells' stage BOUND; the two SLURP `@ts2` cells still stop at `slurp-packet-root-missing`,
and it happens AFTER the stage (the stage's own roster loading only needs the raw derived-media bytes,
which exist; the separate `wire_check` subprocess call needs the speech-feature packet promotion,
which does not). `a2t_input_rate_16k_wire_check.py` -- all 4 cells' stage BOUND, `wire_check` reaches
`stop_class "none"` for all four. `e21_kc_e1_wire_check.py` -- both cells' stage BOUND, verified
directly (the full run's own pre-existing resident-llama-server guard correctly refused to run at all
at verification time, because the main checkout's own GPU flight had a server resident; that refusal
is unrelated to this change).

A second, smaller follow-up remains open (not part of this closure): the three flight-cell scripts
still rebind `carrier_root` to the derived root through the `carrier_root_resolver` seam (§2). That
workaround is now redundant — the declared
root is legal in its own right — and narrowing `carrier_root` away from the real carrier is the
opposite of what confinement wants. Removing it WIDENS what those cells accept (their carrier root
becomes legal again), so it changes live binding behaviour and belongs to its own change with its own
proof, not to this repair. Until then, both mechanisms are in force together and agree: the derived
root is legal either way.
