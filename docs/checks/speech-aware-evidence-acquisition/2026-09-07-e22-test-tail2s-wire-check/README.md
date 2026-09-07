# Zero-contact wire checks — the Earnings-22 tail-silence TEST cell and its 4-row dry run

**BOTH CELLS ARE GREEN. Zero model contacts, zero servers, zero sockets.** Two
`core.flight.FlightRuntime.wire_check` runs — the flight cell at 2,735 rows and its 4-row smoke —
drove the whole request path against `WireCheckGate` and `WireCheckTransport` (which never opens a
socket), and both reached `seal_and_score: OK`: the run manifest was written, verified and scored
through the **real** registered scorers over the transport's canned response, one whole-manifest
job, none failed, empty stderr.

Run under the model-free row `SAEA-SN-MF-E22-TEST-TS2-MEDIA-V1` on the clean committed tree at
commit `599c7b0a`. (An earlier pass at `42da8bb4` was superseded: correcting the pad accounting in
the flight cell's dataset and experiment fragments moved that cell's composed identity, so both
cells were re-run rather than left stale. The smoke's fragments were untouched and its hashes are
therefore unchanged across the two passes.) **Neither cell is authorized**; see
`docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-preregistration.md`, and note that
this cell is a **second read** of the six calibration-exposed ESB test calls and needs the owner's
explicit GO recorded in its own exposure row.

## What passed

| receipt | run id | rows | contacts | model contacts | servers | payload keys = arm-visible fields | `seal_and_score` |
|---|---|---:|---:|---:|---:|---|---|
| `ts2-test-smoke4-wire-check.json` | `SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-SMOKE-V1` | 4 | 4 | **0** | **0** | yes (10) | **OK** |
| `ts2-test-full-wire-check.json` | `SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1` | 2,735 | 2,735 | **0** | **0** | yes (10) | **OK** |

| cell | split id | split identity (flight-computed) | config hash | protocol hash | audio seconds |
|---|---|---|---|---|---:|
| `E22-ESB-2735-TS2` | `E22-ESB-TEST2735-TAIL2S-UTTERANCES` | `ecd9ab76755c…` | `f84f207844ea…` | `f3442e1be030…` | 24,964.608 |
| `E22-ESB-2735-TS2-SMOKE-4` | `E22-ESB-TEST2735-TS2-SMOKE-4` | `f47de393dc03…` | `ab21243840a0…` | `cb8f4e5e65b7…` | 64.760 |

**Both flight-computed split identities equal the ones their dataset fragments declare**, and both
differ from the sealed test population's `9285b321…`, which is the identity separation `D-TS2-1`
exists to guarantee.

## What this proves that the arithmetic could not

1. **The `@ts2`-suffixed sample ids survive the whole path** — roster hydration, media-path
   confinement to `derived/e22-esb-utterances/test2735-tail2s-v1`, the transport payload, the run
   manifest, and, through `reproduction.esb_reference.published_segment_key`, the **reference
   lookup** — on all 2,735 rows. `outputs_row_count` is 2,735 and the scorer job returned
   `succeeded` with return code 0 and an empty stderr, so the ESB reference rail resolved every
   suffixed id back to its published sentence.
2. **The decoding params are the sealed test flight's**: `max_tokens` 1024 with no per-sample cap
   (`max_tokens_policy`, `max_tokens_rule` and `max_tokens_per_sample` are all null) and no stop
   string, `id_slot` per-sample.
3. **The dispatch pins eight slots on the flight and four on the smoke**, which is the sealed test
   flight's `-c 32768 -np 8` geometry.
4. **No packet plane is involved**: `speech_packets_verified` is empty and `tool_schemas_count` is
   0 on both cells, so this is the raw-audio mmproj path with no feature cache and no native-tools
   contract.
5. **The cost accounting reproduces the media facts**: `audio_seconds_used` is 24,964.608437 on the
   flight and 64.760187 on the smoke, which are the build receipt's own totals.

Running the FLIGHT cell here and not only the smoke was deliberate, for the reason the 2026-09-04
wire check already recorded: a manifest that seals `COMPLETED` and then will not score wastes the
GPU time after it has been spent, and on this population that time is a **second read of six
calibration-exposed calls**, which cannot be bought back.

## What the REAL gate does, and why that is also correct

`--dry-run` (the real `contracts.FrozenCoreGate`) was run on both cells. It passes config
composition, roster hydration with a per-file SHA-256 re-hash of all 2,735 media, media-path
confinement, the count check, `ExecutionPlan` construction, the execution-profile check and the WSL
environment assertion, and then **refuses**:

```
GateClosed: model touch refused: run 'SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1' has no
pre-registered exposure row in docs/exposure-ledger.md (rows are written before results are read)
```

That is the correct state. The cell is preregistered and **not authorized**, and everything after
that point (E0 closure, the runtime receipt and GGUF digests, the D1 media-identity rail) is
deliberately not exercised, because exercising it would mean pre-registering an exposure row for a
second test read that has no owner GO.

## One operational note, carried forward

`core.scorers._assert_scoring_entry_gate` calls `require_clean_study_repo`, and that gate refuses
on **any** untracked or modified path, not only the load-bearing surface. Both receipts here were
produced with the tree clean at commit `599c7b0a` and written to a scratchpad directory outside the
repository, then copied in. A flight agent writing receipts into the repository mid-campaign will
hit the same wall.
