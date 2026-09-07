# Earnings-22 DEV model-usage cells (a) and (b) — flight-readiness receipts

Two single-factor cells made **flight-ready and not flown**, on the 1,500-row
`E22-DEV-ESB-1500-V1` subset of this study's own Earnings-22 **dev** subset10. Preregistration:
`docs/readiness/2026-09-06-e22-dev-usage-cells-v1-preregistration.md`. The third cell of that
document, the audio front end, is **CLOSED** (owner 2026-09-06, §3) and has no receipts here.

**Nothing here contacted a model.** Every row that produced these files is model-free: no server was
started, no socket was opened, no GPU was used and no token was generated. That is a statement about
*these* receipts and it still holds. It is no longer a statement about the cells: cell (a) has since
been registered and flown under its own exposure rows, and each cell's flight receipts live in its
own directory rather than here.

| run id | factor | fragments |
|---|---|---|
| `SAEA-E22-DEV-ESB-Q8-V1` | the decoder quantization: Q8_0 instead of the Q4_K_M requant | `q8-e22-dev1500-esb-mmproj-gpu-04ccc72a-np8-c40960` + `e22-esb-dev1500-q8` + `earnings22-esb-dev1500-utterances` + `e22-dev-usage-q8-v1` |
| `SAEA-E22-DEV-ESB-STOPCAP-V1` | the generation cap: `n_predict` resolved per sample from that sample's own duration | `q4km-e22-dev1500-esb-stopcap-mmproj-gpu-04ccc72a-np8-c40960` + `e22-esb-dev1500-stopcap` + `earnings22-esb-dev1500-utterances` + `e22-dev-usage-stopcap-v1` |
| `SAEA-E22-DEV-ESB-Q8-SMOKE-V1` | none — cell (a)'s protocol on the §6.6 four rows | as above with `earnings22-esb-dev1500-smoke4` + `e22-dev-usage-q8-smoke4-v1` |
| `SAEA-E22-DEV-ESB-STOPCAP-SMOKE-V1` | none — cell (b)'s protocol on the same four rows | as above with `earnings22-esb-dev1500-smoke4` + `e22-dev-usage-stopcap-smoke4-v1` |

Both cells are paired row for row against the **sealed** comparator
`SAEA-E22-DEV-ESB-PROMPT-A-V1` (`attempt-20260905T073641Z-f977d1`) restricted to these 1,500 ids, on
identical audio bytes. No new arm A is flown: greedy decoding is not bitwise reproducible across
batch compositions on this runtime.

## What is here

| path | what it pins |
|---|---|
| `q8-placement.json` | cell (a)'s `--n-cpu-moe` placement, **computed offline** from the Q8_0 and mmproj GGUF **headers** (tensor table, no payload, no model load) and calibrated on the A2T probe's own live ladder. `N = 28`, 5,083 MiB projected free against a 3,072 MiB floor; `N = 24` — the A2T probe's own answer — misses by 437 MiB. Files itself as a **PROJECTION**: precondition Q8-P1's live half is still required. |
| `stopcap-resolver.json` | cell (b)'s per-sample cap, resolved through the real registered policy on all 1,500 rows and compared row for row against `analysis.e22_overgeneration.cap_tokens` — the simulator that produced the cell's §2.2 prediction. **0 disagreements**, caps 3–321 tokens, **0 rows at the 1,024 ceiling**. |
| `wire-check/` | the whole request path for all four run ids, through a fake gate and a fake transport — **zero model contacts, zero servers, zero sockets**. |

## The wire checks, and exactly what they prove

Each ran `core.flight.FlightRuntime.wire_check` — the real composed fragments, the real adapter and
samples, the real payload binding, the arm's own dispatch and the whole
`FrozenCoreClient`/`FrozenCoreAdapter` stack including its payload allowlist and attempt accounting.
The only fakes are two: `WireCheckGate` (authorizes nothing real) and `WireCheckTransport` (never
opens a socket).

| run id | requests | payload keys | `id_slot` | `max_tokens` at the wire |
|---|---:|---|---|---|
| `SAEA-E22-DEV-ESB-Q8-V1` | 1,500 | = `ARM_VISIBLE_FIELDS["bare-core"]` | integer, 8 slots | the integer `1024`, unchanged from the comparator |
| `SAEA-E22-DEV-ESB-STOPCAP-V1` | 1,500 | = `ARM_VISIBLE_FIELDS["bare-core"]` | integer, 8 slots | **1,500 per-sample integers, 3 to 321**, each re-derived at the transport seam from that request's own `audio_seconds` |
| `SAEA-E22-DEV-ESB-Q8-SMOKE-V1` | 4 | same | integer | `1024` |
| `SAEA-E22-DEV-ESB-STOPCAP-SMOKE-V1` | 4 | same | integer | `3`, `55`, `127`, `321` |

The stop-cap receipts carry `max_tokens_per_sample`: every request's resolved integer, keyed by
sample id. The check does not merely record it — it recomputes the policy's own answer for each
request's `audio_seconds` at the seam and **refuses** if the two disagree. That is the observable
proof that the cap was resolved per sample and not once for the cell.

Each wire check opens its own `WIRECHECK-…` run id and aborts that attempt before returning, so no
registered run's durable accounting is touched.

## Where these were run, and what must be re-run

They ran in the `wt/e22b` worktree at commit `3f33234e`, through the **committed**
`scripts/flights/run_e22_esb_cell.py` `build_runtime` with only its `REPO` constant repointed at the
worktree. The committed launcher is unmodified and its primary-checkout pin — which exists so a
FLIGHT cannot run from a worktree — is untouched.

That proves the request path, the payload allowlist, the dispatch and the per-request resolved cap,
none of which depends on which checkout the code sits in. It does **not** replace the primary
checkout's own run: `study_commit` and the clean-tree assertion the seal half exercises are
checkout-specific, and so is the launcher's pin. **Re-run
`scripts/flights/run_e22_esb_cell.py --wire-check` on the primary checkout, unpatched, immediately
before the flight** (§7.6 of the preregistration) and land its receipt beside these.

Only documents and receipts were added after `3f33234e`; no code changed, so these receipts describe
the code as it stands.

## The primary-checkout re-run of the Q8 wire checks (2026-09-06)

Section 7.6 of the preregistration requires
`scripts/flights/run_e22_esb_cell.py --wire-check` to be re-run **on the primary checkout,
unpatched, immediately before the flight**, because `study_commit`, the clean-tree assertion the
seal half exercises, and the launcher's own `REPO` pin are checkout-specific. That re-run is landed
here for cell (a)'s two run ids, at commit `207c829a` on a clean tree, through the committed
launcher with nothing repointed:

| file | run id | contacts | seal half |
|---|---|---:|---|
| `wire-check/wire-check-q8-flight-1500-primary.json` | `SAEA-E22-DEV-ESB-Q8-V1` | 1,500 | `OK` |
| `wire-check/wire-check-q8-smoke-4-primary.json` | `SAEA-E22-DEV-ESB-Q8-SMOKE-V1` | 4 | `OK` |

Both reproduce the composed identities the preregistration fixed before any of this existed:
`config_hash` `8789a5ab…` / `protocol_hash` `c77a10ac…` / `split_identity_hash` `c626e62f…` for the
flight, and `348506249b…` / `605b30f7…` / `c5b9886a…` for the four-row dry run. Payload keys are
exactly `ARM_VISIBLE_FIELDS["bare-core"]` (ten fields), `id_slot` is an integer over the eight slots
and `max_tokens` is the integer `1024` on every request — cell (a) carries no per-sample cap. Still
**zero model contacts, zero servers, zero sockets**: the only fakes are `WireCheckGate` and
`WireCheckTransport`.

The stop-cap cell's own primary-checkout re-run is the section below.

## The primary-checkout re-run of the stop-cap wire checks (2026-09-07)

The same §7.6 obligation, discharged for cell (b)'s two run ids immediately before its flight, at
commit `5d357e20` on a clean tree, through the committed launcher with nothing repointed:

| file | run id | contacts | seal half |
|---|---|---:|---|
| `wire-check/wire-check-stopcap-flight-1500-primary.json` | `SAEA-E22-DEV-ESB-STOPCAP-V1` | 1,500 | `OK` |
| `wire-check/wire-check-stopcap-smoke-4-primary.json` | `SAEA-E22-DEV-ESB-STOPCAP-SMOKE-V1` | 4 | `OK` |

Both reproduce the composed identities §2.3.1 of the preregistration fixed before any of this
existed: `config_hash` `d47999a6…` / `protocol_hash` `4fda9f67…` / `split_identity_hash`
`c626e62f…` for the flight, and `78205c9e…` / `e03ec753…` / `c5b9886a…` for the four-row dry
run. Payload keys are exactly `ARM_VISIBLE_FIELDS["bare-core"]` (ten fields) and `id_slot` is an
integer over the eight slots.

**The cap survives the checkout change unchanged.** `max_tokens_per_sample` on the primary checkout
carries 1,500 integers, **202 distinct values from 3 to 321, none at the 1,024 ceiling**, and it is
**equal row for row** both to `stopcap-resolver.json`'s `caps_by_sample_id` (0 disagreements over
1,500 rows) and to the `wt/e22b` receipt's own mapping. The four dry-run rows resolve to `3`, `55`,
`127` and `321` as registered. `request_body_sha256` differs from the worktree receipt's, as cell
(a)'s re-run also did, because each wire check mints its own `WIRECHECK-…` run id and that id enters
`request_id`; nothing else in the body moves.

Still **zero model contacts, zero servers, zero sockets**: the only fakes are `WireCheckGate` and
`WireCheckTransport`, and each check aborts its own throwaway attempt before returning.
